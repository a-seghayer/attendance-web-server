# إعداد Firebase Admin SDK لخادم PreStaff
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# متغير عام لقاعدة البيانات
db = None

def initialize_firebase():
    """تهيئة Firebase Admin SDK"""
    global db
    
    try:
        # التحقق من وجود Firebase مُهيأ مسبقاً
        if firebase_admin._apps:
            print("Firebase already initialized")
            db = firestore.client()
            return True
            
        # البحث عن مفتاح الخدمة
        service_account_path = None
        
        # البحث في مسارات مختلفة
        possible_paths = [
            'serviceAccountKey.json',
            './serviceAccountKey.json',
            '../serviceAccountKey.json',
            os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                service_account_path = path
                break
        
        # إذا لم نجد الملف، نحاول استخدام متغير البيئة
        if not service_account_path:
            firebase_credentials = os.getenv('FIREBASE_CREDENTIALS')
            if firebase_credentials:
                # إنشاء ملف مؤقت من متغير البيئة
                with open('temp_service_account.json', 'w') as f:
                    f.write(firebase_credentials)
                service_account_path = 'temp_service_account.json'
        
        if not service_account_path:
            print("❌ لم يتم العثور على مفتاح الخدمة")
            return False
        
        # تهيئة Firebase
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        
        # الاتصال بـ Firestore
        db = firestore.client()
        
        print("✅ تم تهيئة Firebase بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة Firebase: {str(e)}")
        return False

def get_db():
    """الحصول على مرجع قاعدة البيانات"""
    global db
    if db is None:
        initialize_firebase()
    return db

# === وظائف المستخدمين ===

def get_user_by_username(username):
    """البحث عن مستخدم بالاسم"""
    try:
        db = get_db()
        if not db:
            return None
            
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', username)
        docs = list(query.stream())
        
        if docs:
            user_data = docs[0].to_dict()
            user_data['doc_id'] = docs[0].id
            return user_data
        return None
        
    except Exception as e:
        print(f"خطأ في البحث عن المستخدم: {str(e)}")
        return None

def create_user(user_data):
    """إنشاء مستخدم جديد"""
    try:
        db = get_db()
        if not db:
            return False
            
        # الحصول على أعلى ID
        users_ref = db.collection('users')
        all_users = users_ref.stream()
        max_id = 0
        
        for user in all_users:
            user_dict = user.to_dict()
            if 'id' in user_dict and user_dict['id'] > max_id:
                max_id = user_dict['id']
        
        # إضافة المستخدم الجديد
        new_user_data = {
            'id': max_id + 1,
            'username': user_data['username'],
            'passwordHash': user_data['password_hash'],
            'isSuperadmin': user_data.get('is_superadmin', False),
            'services': user_data.get('services', ''),
            'createdAt': datetime.utcnow()
        }
        
        doc_ref = users_ref.add(new_user_data)
        print(f"✅ تم إنشاء المستخدم: {user_data['username']}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء المستخدم: {str(e)}")
        return False

def get_all_users():
    """جلب جميع المستخدمين"""
    try:
        db = get_db()
        if not db:
            return []
            
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        users = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data['doc_id'] = doc.id
            users.append(user_data)
            
        return users
        
    except Exception as e:
        print(f"خطأ في جلب المستخدمين: {str(e)}")
        return []

# === وظائف الطلبات المعلقة ===

def get_pending_users():
    """جلب طلبات الحسابات المعلقة"""
    try:
        db = get_db()
        if not db:
            return []
            
        pending_ref = db.collection('pendingUsers')
        docs = pending_ref.order_by('createdAt').stream()
        
        pending_users = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data['doc_id'] = doc.id
            pending_users.append(user_data)
            
        return pending_users
        
    except Exception as e:
        print(f"خطأ في جلب الطلبات المعلقة: {str(e)}")
        return []

def add_pending_user(username, password_hash):
    """إضافة طلب حساب معلق"""
    try:
        db = get_db()
        if not db:
            return False
            
        # التحقق من عدم وجود المستخدم
        existing_user = get_user_by_username(username)
        if existing_user:
            return False
            
        # التحقق من عدم وجود طلب معلق
        pending_ref = db.collection('pendingUsers')
        existing_pending = pending_ref.where('username', '==', username).stream()
        if list(existing_pending):
            return False
            
        # الحصول على أعلى ID
        all_pending = pending_ref.stream()
        max_id = 0
        
        for pending in all_pending:
            pending_dict = pending.to_dict()
            if 'id' in pending_dict and pending_dict['id'] > max_id:
                max_id = pending_dict['id']
        
        # إضافة الطلب المعلق
        pending_data = {
            'id': max_id + 1,
            'username': username,
            'passwordHash': password_hash,
            'createdAt': datetime.utcnow()
        }
        
        pending_ref.add(pending_data)
        print(f"✅ تم إضافة طلب معلق: {username}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إضافة الطلب المعلق: {str(e)}")
        return False

def approve_pending_user(username, services=""):
    """الموافقة على طلب حساب معلق"""
    try:
        db = get_db()
        if not db:
            return False
            
        # البحث عن الطلب المعلق
        pending_ref = db.collection('pendingUsers')
        pending_query = pending_ref.where('username', '==', username)
        pending_docs = list(pending_query.stream())
        
        if not pending_docs:
            return False
            
        pending_data = pending_docs[0].to_dict()
        
        # إنشاء المستخدم الجديد
        user_data = {
            'username': pending_data['username'],
            'password_hash': pending_data['passwordHash'],
            'is_superadmin': False,
            'services': services
        }
        
        success = create_user(user_data)
        
        if success:
            # حذف الطلب المعلق
            pending_docs[0].reference.delete()
            print(f"✅ تم قبول المستخدم: {username}")
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ خطأ في قبول المستخدم: {str(e)}")
        return False

def reject_pending_user(username):
    """رفض طلب حساب معلق"""
    try:
        db = get_db()
        if not db:
            return False
            
        # البحث عن الطلب المعلق وحذفه
        pending_ref = db.collection('pendingUsers')
        pending_query = pending_ref.where('username', '==', username)
        pending_docs = list(pending_query.stream())
        
        if pending_docs:
            pending_docs[0].reference.delete()
            print(f"✅ تم رفض المستخدم: {username}")
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ خطأ في رفض المستخدم: {str(e)}")
        return False

# === وظائف الطلبات ===

def create_request(request_data):
    """إنشاء طلب جديد (إضافي/إجازة)"""
    try:
        db = get_db()
        if not db:
            return False
            
        # الحصول على أعلى ID
        requests_ref = db.collection('requests')
        all_requests = requests_ref.stream()
        max_id = 0
        
        for request in all_requests:
            request_dict = request.to_dict()
            if 'id' in request_dict and request_dict['id'] > max_id:
                max_id = request_dict['id']
        
        # إنشاء الطلب الجديد
        new_request_data = {
            'id': max_id + 1,
            'employeeId': request_data['employee_id'],
            'kind': request_data['kind'],
            'reqDate': request_data['date'],
            'reason': request_data.get('reason', ''),
            'supervisor': request_data['supervisor'],
            'createdAt': datetime.utcnow(),
            'executedAt': datetime.utcnow(),
            'status': 'active',
            'canceledBy': None,
            'canceledAt': None
        }
        
        requests_ref.add(new_request_data)
        print(f"✅ تم إنشاء الطلب: {request_data['kind']} للموظف {request_data['employee_id']}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الطلب: {str(e)}")
        return False

def get_latest_requests(limit=10):
    """جلب أحدث الطلبات"""
    try:
        db = get_db()
        if not db:
            return []
            
        requests_ref = db.collection('requests')
        docs = requests_ref.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        requests = []
        for doc in docs:
            request_data = doc.to_dict()
            request_data['id'] = doc.id  # إضافة ID للطلب
            
            # تحويل التواريخ إلى نص
            if 'createdAt' in request_data and request_data['createdAt']:
                request_data['created_at'] = request_data['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
            if 'executedAt' in request_data and request_data['executedAt']:
                request_data['executed_at'] = request_data['executedAt'].strftime('%Y-%m-%d %H:%M:%S')
            if 'canceledAt' in request_data and request_data['canceledAt']:
                request_data['canceled_at'] = request_data['canceledAt'].strftime('%Y-%m-%d %H:%M:%S')
            
            # توحيد أسماء الحقول
            if 'employeeId' in request_data:
                request_data['employee_id'] = request_data['employeeId']
            if 'canceledBy' in request_data:
                request_data['canceled_by'] = request_data['canceledBy']
            if 'reqDate' in request_data:
                request_data['date'] = request_data['reqDate']
                
            requests.append(request_data)
            
        return requests
        
    except Exception as e:
        print(f"خطأ في جلب الطلبات: {str(e)}")
        return []

def cancel_request(request_id, canceled_by):
    """إلغاء طلب"""
    try:
        db = get_db()
        if not db:
            return False
            
        # البحث عن الطلب بـ ID
        requests_ref = db.collection('requests')
        query = requests_ref.where('id', '==', int(request_id))
        docs = list(query.stream())
        
        if docs:
            doc_ref = docs[0].reference
            doc_ref.update({
                'status': 'canceled',
                'canceledBy': canceled_by,
                'canceledAt': datetime.utcnow().isoformat()
            })
            print(f"✅ تم إلغاء الطلب: {request_id}")
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ خطأ في إلغاء الطلب: {str(e)}")
        return False

# تهيئة Firebase عند استيراد الملف
if __name__ != "__main__":
    initialize_firebase()
