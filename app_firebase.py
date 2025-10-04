import io
import os
import sys
import tempfile
import zipfile
from datetime import datetime, date
from typing import Dict, Any

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# استيراد إعداد Firebase
from firebase_config import (
    initialize_firebase,
    get_user_by_username,
    create_user,
    get_all_users,
    get_pending_users,
    add_pending_user,
    approve_pending_user,
    reject_pending_user,
    create_request,
    get_latest_requests,
    cancel_request
)

# Ensure we can import attendance_processor from parent directory
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CUR_DIR, os.pardir))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from attendance_processor import (
    process_workbook,
    parse_holidays,
)
from openpyxl import Workbook

app = Flask(__name__)
CORS(app)  # Allow static site to call the API

# Configure JSON to handle Arabic text properly
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Helper function for UTF-8 JSON responses
def json_response(data, status_code=200):
    """Create JSON response with proper UTF-8 encoding for Arabic text"""
    response = jsonify(data)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response, status_code

# Config
SECRET = os.environ.get("APP_SECRET", "CHANGE_ME_SECRET")

# تهيئة Firebase عند بدء التطبيق
firebase_initialized = initialize_firebase()
if not firebase_initialized:
    print("⚠️ تحذير: فشل في تهيئة Firebase، سيتم استخدام البيانات الوهمية")
else:
    # إنشاء المستخدم الافتراضي إذا لم يكن موجوداً
    try:
        admin_user = get_user_by_username("anas")
        if not admin_user:
            admin_data = {
                'username': 'anas',
                'password_hash': generate_password_hash(os.environ.get('DEFAULT_ADMIN_PASSWORD', 'TempPass123!')),
                'is_superadmin': True,
                'services': 'attendance,overtime',
                'is_active': True
            }
            create_user(admin_data)
            print("✅ تم إنشاء المستخدم الافتراضي 'anas'")
        else:
            print("✅ المستخدم الافتراضي 'anas' موجود بالفعل")
    except Exception as e:
        print(f"⚠️ خطأ في إنشاء المستخدم الافتراضي: {str(e)}")

def create_token(username: str, is_superadmin: bool, services: str) -> str:
    payload = {
        "sub": username,
        "admin": is_superadmin,
        "srv": services,
        "iat": int(datetime.utcnow().timestamp()),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def require_auth(required_service: str = None):
    def wrapper(fn):
        def inner(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return ("Unauthorized", 401)
            token = auth.split(" ", 1)[1]
            try:
                data = jwt.decode(token, SECRET, algorithms=["HS256"])
            except Exception:
                return ("Invalid token", 401)
            request.user = data
            if required_service and (not data.get("admin")):
                srv = (data.get("srv") or "")
                allowed = [s.strip() for s in srv.split(',') if s.strip()]
                if required_service not in allowed:
                    return ("Forbidden", 403)
            return fn(*args, **kwargs)
        inner.__name__ = fn.__name__
        return inner
    return wrapper

# === نقاط النهاية للمصادقة ===

@app.route("/api/login", methods=["POST"])
def login():
    """تسجيل الدخول باستخدام Firebase"""
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        if not username or not password:
            return jsonify({"error": "اسم المستخدم وكلمة المرور مطلوبان"}), 400
        
        user = get_user_by_username(username)
        if not user:
            return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401
        
        # التحقق من كلمة المرور
        if not user or not check_password_hash(user.get('passwordHash', ''), password):
            return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيحة"}), 401
        
        # التحقق من حالة الحساب
        if not user.get('is_active', True):
            return jsonify({"error": "تم تعطيل هذا الحساب. تواصل مع الإدارة."}), 403
        
        token = create_token(
            username=user['username'],
            is_superadmin=user.get('isSuperadmin', False),
            services=user.get('services', '')
        )
        
        return jsonify({
            "token": token,
            "username": user['username'],
            "is_superadmin": user.get('isSuperadmin', False),
            "services": user.get('services', '').split(',') if user.get('services') else []
        })
        
    except Exception as e:
        print(f"خطأ في تسجيل الدخول: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/signup", methods=["POST"])
def signup():
    """طلب إنشاء حساب جديد"""
    try:
        data = request.get_json()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        
        if not username or not password:
            return jsonify({"error": "اسم المستخدم وكلمة المرور مطلوبان"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل"}), 400
        
        # التحقق من عدم وجود المستخدم
        existing_user = get_user_by_username(username)
        if existing_user:
            return json_response({"error": "اسم المستخدم موجود بالفعل"}, 400)
        
        # إضافة طلب معلق
        password_hash = generate_password_hash(password)
        success = add_pending_user(username, password_hash)
        
        if success:
            return json_response({"message": "تم إرسال طلبك، في انتظار موافقة المدير"})
        else:
            return json_response({"error": "فشل في إرسال الطلب"}, 500)
            
    except Exception as e:
        print(f"خطأ في التسجيل: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

# === نقاط النهاية الإدارية ===

@app.route("/api/admin/pending", methods=["GET"])
@require_auth()
def get_pending():
    """جلب طلبات الحسابات المعلقة (للمدراء فقط)"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        pending_users = get_pending_users()
        
        # تحويل التواريخ إلى نص
        for user in pending_users:
            if 'createdAt' in user and user['createdAt']:
                user['created_at'] = user['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(pending_users)
        
    except Exception as e:
        print(f"خطأ في جلب الطلبات المعلقة: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/admin/approve", methods=["POST"])
@require_auth()
def approve_user():
    """الموافقة على طلب حساب"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        data = request.get_json()
        username = data.get("username", "").strip()
        services = data.get("services", [])
        
        if not username:
            return jsonify({"error": "اسم المستخدم مطلوب"}), 400
        
        # تحويل services من array إلى string
        services_str = ','.join(services) if isinstance(services, list) else str(services)
        
        success = approve_pending_user(username, services_str)
        
        if success:
            return jsonify({"message": "تم قبول المستخدم بنجاح"})
        else:
            return jsonify({"error": "فشل في قبول المستخدم"}), 500
            
    except Exception as e:
        print(f"خطأ في قبول المستخدم: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/admin/reject", methods=["POST"])
@require_auth()
def reject_user():
    """رفض طلب حساب"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        data = request.get_json()
        username = data.get("username", "").strip()
        
        if not username:
            return jsonify({"error": "اسم المستخدم مطلوب"}), 400
        
        success = reject_pending_user(username)
        
        if success:
            return jsonify({"message": "تم رفض المستخدم"})
        else:
            return jsonify({"error": "فشل في رفض المستخدم"}), 500
            
    except Exception as e:
        print(f"خطأ في رفض المستخدم: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/admin/users", methods=["GET"])
@require_auth()
def get_users():
    """جلب جميع المستخدمين (للمدراء فقط)"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        users = get_all_users()
        
        # إخفاء كلمات المرور وتحويل التواريخ وتحويل services إلى array
        for user in users:
            user.pop('passwordHash', None)
            if 'createdAt' in user and user['createdAt']:
                user['created_at'] = user['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
            # تحويل services من string إلى array
            if 'services' in user:
                if isinstance(user['services'], str):
                    user['services'] = user['services'].split(',') if user['services'] else []
        
        return jsonify(users)
        
    except Exception as e:
        print(f"خطأ في جلب المستخدمين: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/admin/users", methods=["POST"])
@require_auth()
def create_user_admin():
    """إنشاء مستخدم جديد (للمدراء فقط)"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        data = request.get_json()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        services = data.get("services", [])
        
        if not username or not password:
            return jsonify({"error": "اسم المستخدم وكلمة المرور مطلوبان"}), 400
        
        # تحقق من وجود المستخدم
        existing_user = get_user_by_username(username)
        if existing_user:
            return json_response({"error": "اسم المستخدم موجود بالفعل"}, 400)
        
        # تحويل services إلى string
        services_str = ','.join(services) if isinstance(services, list) else str(services)
        
        # إنشاء المستخدم
        user_data = {
            'username': username,
            'password_hash': generate_password_hash(password),
            'is_superadmin': False,
            'services': services_str,
            'is_active': True
        }
        
        success = create_user(user_data)
        
        if success:
            return jsonify({"message": "تم إنشاء المستخدم بنجاح"})
        else:
            return jsonify({"error": "فشل في إنشاء المستخدم"}), 500
        
    except Exception as e:
        print(f"خطأ في إنشاء المستخدم: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/admin/toggle-status", methods=["POST"])
@require_auth()
def toggle_user_status():
    """تفعيل/تعطيل حساب مستخدم (للمدراء فقط)"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        data = request.get_json()
        username = data.get("username", "").strip()
        
        if not username:
            return jsonify({"error": "اسم المستخدم مطلوب"}), 400
        
        # جلب المستخدم الحالي
        user = get_user_by_username(username)
        if not user:
            return jsonify({"error": "المستخدم غير موجود"}), 404
        
        # تبديل حالة الحساب
        current_status = user.get('is_active', True)
        new_status = not current_status
        
        # تحديث الحساب في قاعدة البيانات
        from firebase_config import get_db
        db = get_db()
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', username).limit(1)
        docs = query.stream()
        
        updated = False
        for doc in docs:
            doc.reference.update({'is_active': new_status})
            updated = True
            break
        
        if updated:
            status_text = "تم تفعيل" if new_status else "تم تعطيل"
            return jsonify({"message": f"{status_text} حساب المستخدم '{username}' بنجاح"})
        else:
            return jsonify({"error": "فشل في تحديث حالة المستخدم"}), 500
        
    except Exception as e:
        print(f"خطأ في تبديل حالة المستخدم: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/admin/users/update", methods=["POST"])
@require_auth()
def update_user():
    """تحديث بيانات مستخدم (للمدراء فقط)"""
    try:
        if not request.user.get("admin"):
            return jsonify({"error": "غير مسموح"}), 403
        
        data = request.get_json()
        old_username = data.get("old_username", "").strip()  # اسم المستخدم الحالي
        new_username = data.get("username", "").strip()      # اسم المستخدم الجديد
        services = data.get("services", [])
        password = data.get("password", "").strip()
        
        # استخدام old_username للبحث، أو username إذا لم يتم توفير old_username
        search_username = old_username if old_username else new_username
        
        if not search_username:
            return jsonify({"error": "اسم المستخدم مطلوب"}), 400
        
        # جلب المستخدم الحالي
        user = get_user_by_username(search_username)
        if not user:
            return jsonify({"error": "المستخدم غير موجود"}), 404
        
        # تحضير البيانات للتحديث
        update_data = {}
        
        # تحديث اسم المستخدم إذا تغير
        if new_username and new_username != search_username:
            # التحقق من عدم وجود اسم المستخدم الجديد
            existing_user = get_user_by_username(new_username)
            if existing_user:
                return jsonify({"error": f"اسم المستخدم '{new_username}' موجود بالفعل"}), 400
            update_data['username'] = new_username
        
        # تحديث الخدمات
        if services:
            services_str = ','.join(services) if isinstance(services, list) else str(services)
            update_data['services'] = services_str
        
        # تحديث كلمة المرور إذا تم توفيرها
        if password:
            update_data['passwordHash'] = generate_password_hash(password)
        
        if not update_data:
            return jsonify({"error": "لا توجد بيانات للتحديث"}), 400
        
        # تحديث المستخدم في قاعدة البيانات
        from firebase_config import get_db
        db = get_db()
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', search_username).limit(1)
        docs = query.stream()
        
        updated = False
        for doc in docs:
            doc.reference.update(update_data)
            updated = True
            break
        
        if updated:
            final_username = new_username if new_username and new_username != search_username else search_username
            return jsonify({"message": f"تم تحديث بيانات المستخدم '{final_username}' بنجاح"})
        else:
            return jsonify({"error": "فشل في تحديث المستخدم"}), 500
        
    except Exception as e:
        print(f"خطأ في تحديث المستخدم: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

# === نقاط النهاية للطلبات ===

@app.route("/api/requests/create", methods=["POST"])
@require_auth("overtime")
def create_request_endpoint():
    """إنشاء طلب جديد (إضافي/إجازة)"""
    try:
        data = request.get_json()
        employee_id = data.get("employee_id", "").strip()
        kind = data.get("kind", "").strip()
        req_date = data.get("date", "").strip()
        reason = data.get("reason", "").strip()
        
        if not employee_id or not kind or not req_date:
            return jsonify({"error": "معرف الموظف ونوع الطلب والتاريخ مطلوبة"}), 400
        
        if kind not in ["overtime", "leave"]:
            return jsonify({"error": "نوع الطلب يجب أن يكون overtime أو leave"}), 400
        
        # إنشاء الطلب
        request_data = {
            "employee_id": employee_id,
            "kind": kind,
            "date": req_date,
            "reason": reason,
            "supervisor": request.user.get("sub", "")
        }
        
        success = create_request(request_data)
        
        if success:
            return jsonify({"message": "تم إنشاء الطلب بنجاح"})
        else:
            return jsonify({"error": "فشل في إنشاء الطلب"}), 500
            
    except Exception as e:
        print(f"خطأ في إنشاء الطلب: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/requests/latest", methods=["GET"])
@require_auth("overtime")
def get_latest_requests_endpoint():
    """جلب أحدث الطلبات"""
    try:
        limit = int(request.args.get("limit", 10))
        requests = get_latest_requests(limit)
        
        return jsonify(requests)
        
    except Exception as e:
        print(f"خطأ في جلب الطلبات: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

@app.route("/api/requests/cancel", methods=["POST"])
@require_auth("overtime")
def cancel_request_endpoint():
    """إلغاء طلب"""
    try:
        data = request.get_json()
        request_id = data.get("id")
        
        if not request_id:
            return jsonify({"error": "معرف الطلب مطلوب"}), 400
        
        success = cancel_request(request_id, request.user.get("sub", ""))
        
        if success:
            return jsonify({"message": "تم إلغاء الطلب بنجاح"})
        else:
            return jsonify({"error": "فشل في إلغاء الطلب"}), 500
            
    except Exception as e:
        print(f"خطأ في إلغاء الطلب: {str(e)}")
        return jsonify({"error": "خطأ في الخادم"}), 500

# === نقاط النهاية لمعالج الحضور (تبقى كما هي) ===

@app.route("/api/attendance/process", methods=["POST"])
@require_auth("attendance")
def process_attendance():
    """معالجة ملف الحضور"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "لم يتم رفع أي ملف"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "لم يتم اختيار ملف"}), 400
        
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({"error": "نوع الملف غير مدعوم. يرجى رفع ملف Excel"}), 400
        
        # حفظ الملف مؤقتاً
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # معالجة الملف - جمع جميع المعاملات
            sheet_name = request.form.get("sheet", None) or None
            target_days = int(request.form.get("target_days", 26))
            holidays_str = request.form.get("holidays", "")
            holidays = parse_holidays(holidays_str) if holidays_str else set()
            special_days_str = request.form.get("special_days", "")
            special_days = parse_holidays(special_days_str) if special_days_str else set()
            cutoff_hour = int(request.form.get("cutoff_hour", 7))
            fmt = request.form.get("format", "auto")
            allow_negative = request.form.get("allow_negative", "0") == "1"
            
            # استدعاء دالة المعالجة بجميع المعاملات
            summary_results, daily_results = process_workbook(
                path=temp_path,
                sheet_name=sheet_name,
                target_days=target_days,
                holidays=holidays,
                special_days=special_days,
                fmt=fmt,
                cutoff_hour=cutoff_hour
            )
            
            # إنشاء ملف ZIP يحتوي على التقارير
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # إنشاء ملف الملخص
                summary_wb = Workbook()
                summary_ws = summary_wb.active
                summary_ws.title = "ملخص الحضور"
                
                # إضافة عناوين الملخص
                summary_headers = ["الموظف", "أيام العمل المستهدفة", "أيام الحضور", "أيام الغياب", 
                                 "ساعات العمل", "ساعات الإضافي", "التأخير (دقائق)", "الحالة"]
                for col, header in enumerate(summary_headers, 1):
                    summary_ws.cell(row=1, column=col, value=header)
                
                # إضافة بيانات الملخص
                for row, result in enumerate(summary_results, 2):
                    summary_ws.cell(row=row, column=1, value=result.get('employee_id', ''))
                    summary_ws.cell(row=row, column=2, value=result.get('target_days', 0))
                    summary_ws.cell(row=row, column=3, value=result.get('attendance_days', 0))
                    summary_ws.cell(row=row, column=4, value=result.get('absent_days', 0))
                    summary_ws.cell(row=row, column=5, value=result.get('total_hours', 0))
                    summary_ws.cell(row=row, column=6, value=result.get('overtime_hours', 0))
                    summary_ws.cell(row=row, column=7, value=result.get('late_minutes', 0))
                    summary_ws.cell(row=row, column=8, value=result.get('status', ''))
                
                # حفظ ملف الملخص في الذاكرة
                summary_buffer = io.BytesIO()
                summary_wb.save(summary_buffer)
                summary_buffer.seek(0)
                zip_file.writestr("Summary_Report.xlsx", summary_buffer.getvalue())
                
                # إنشاء ملف التفاصيل اليومية
                daily_wb = Workbook()
                daily_ws = daily_wb.active
                daily_ws.title = "التفاصيل اليومية"
                
                # إضافة عناوين التفاصيل اليومية
                daily_headers = ["الموظف", "التاريخ", "أول دخول", "آخر خروج", "ساعات العمل", 
                               "ساعات الإضافي", "التأخير (دقائق)", "ملاحظات"]
                for col, header in enumerate(daily_headers, 1):
                    daily_ws.cell(row=1, column=col, value=header)
                
                # إضافة بيانات التفاصيل اليومية
                for row, daily in enumerate(daily_results, 2):
                    daily_ws.cell(row=row, column=1, value=daily.get('employee_id', ''))
                    daily_ws.cell(row=row, column=2, value=daily.get('date', ''))
                    daily_ws.cell(row=row, column=3, value=daily.get('first_in', ''))
                    daily_ws.cell(row=row, column=4, value=daily.get('last_out', ''))
                    daily_ws.cell(row=row, column=5, value=daily.get('work_hours', 0))
                    daily_ws.cell(row=row, column=6, value=daily.get('overtime_hours', 0))
                    daily_ws.cell(row=row, column=7, value=daily.get('late_minutes', 0))
                    daily_ws.cell(row=row, column=8, value=daily.get('notes', ''))
                
                # حفظ ملف التفاصيل في الذاكرة
                daily_buffer = io.BytesIO()
                daily_wb.save(daily_buffer)
                daily_buffer.seek(0)
                zip_file.writestr("Daily_Details.xlsx", daily_buffer.getvalue())
            
            zip_buffer.seek(0)
            
            # إرسال ملف ZIP
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=f"attendance_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mimetype='application/zip'
            )
            
        finally:
            # تنظيف الملفات المؤقتة
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        print(f"خطأ في معالجة الحضور: {str(e)}")
        return jsonify({"error": f"خطأ في معالجة الملف: {str(e)}"}), 500

# === نقاط النهاية العامة ===

@app.route("/api/health", methods=["GET"])
def health():
    """فحص صحة الخادم"""
    return jsonify({
        "status": "healthy",
        "firebase": firebase_initialized,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/", methods=["GET"])
def root():
    """الصفحة الرئيسية"""
    return jsonify({
        "message": "PreStaff API Server with Firebase",
        "version": "2.0.0",
        "firebase_enabled": firebase_initialized
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
