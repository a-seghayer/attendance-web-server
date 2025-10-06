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
            print("❌ لم يتم العثور على مفتاح الخدمة Firebase")
            print("💡 تحتاج إلى:")
            print("   1. تحميل ملف serviceAccountKey.json من Firebase Console")
            print("   2. وضعه في مجلد web_server")
            print("   3. أو تعيين متغير البيئة FIREBASE_CREDENTIALS")
            return False
        
        # تهيئة Firebase
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        
        # الاتصال بـ Firestore
        db = firestore.client()
        
        print("✅ تم تهيئة Firebase بنجاح")
        
        # إنشاء collections الأساسية إذا لم تكن موجودة
        initialize_collections()
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة Firebase: {str(e)}")
        return False

def initialize_collections():
    """إنشاء collections الأساسية إذا لم تكن موجودة"""
    try:
        global db
        if not db:
            return
            
        print("🔧 التحقق من collections الأساسية...")
        
        # قائمة collections المطلوبة
        required_collections = ['users', 'pendingUsers', 'requests']
        
        for collection_name in required_collections:
            try:
                # محاولة قراءة collection للتحقق من وجوده
                collection_ref = db.collection(collection_name)
                docs = list(collection_ref.limit(1).stream())
                
                if not docs:
                    print(f"📁 إنشاء collection: {collection_name}")
                    # إنشاء document وهمي لإنشاء collection
                    dummy_doc = {
                        '_initialized': True,
                        'createdAt': datetime.utcnow(),
                        'note': f'Auto-created {collection_name} collection'
                    }
                    collection_ref.document('_init').set(dummy_doc)
                    print(f"✅ تم إنشاء collection: {collection_name}")
                else:
                    print(f"✅ collection موجود: {collection_name}")
                    
            except Exception as e:
                print(f"⚠️ تحذير: مشكلة مع collection {collection_name}: {e}")
                
        print("🎯 تم التحقق من جميع collections الأساسية")
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة collections: {str(e)}")

def get_db():
    """الحصول على مرجع قاعدة البيانات"""
    global db
    if db is None:
        print("🔄 تهيئة Firebase...")
        success = initialize_firebase()
        if not success:
            print("❌ فشل في تهيئة Firebase")
            return None
    
    if db is None:
        print("❌ قاعدة البيانات غير متاحة")
        return None
    
    print("✅ قاعدة البيانات متاحة")
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
        print("🔄 جلب قائمة المستخدمين المعلقين...")
        db = get_db()
        if not db:
            print("❌ فشل في الحصول على قاعدة البيانات")
            return []
            
        pending_ref = db.collection('pendingUsers')
        
        try:
            # تجاهل documents التهيئة
            docs = pending_ref.where('_initialized', '!=', True).order_by('createdAt').stream()
            
            pending_users = []
            for doc in docs:
                user_data = doc.to_dict()
                # تجاهل documents التهيئة
                if user_data.get('_initialized'):
                    continue
                    
                user_data['doc_id'] = doc.id
                pending_users.append(user_data)
                print(f"📄 عثر على مستخدم معلق: {user_data.get('username', 'unknown')}")
            
            print(f"✅ تم جلب {len(pending_users)} مستخدم معلق")
            return pending_users
            
        except Exception as query_error:
            print(f"⚠️ خطأ في الاستعلام، محاولة بديلة: {query_error}")
            # محاولة بديلة بدون order_by
            docs = pending_ref.stream()
            pending_users = []
            for doc in docs:
                user_data = doc.to_dict()
                # تجاهل documents التهيئة
                if user_data.get('_initialized'):
                    continue
                    
                user_data['doc_id'] = doc.id
                pending_users.append(user_data)
                
            return pending_users
        
    except Exception as e:
        print(f"❌ خطأ في جلب الطلبات المعلقة: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def add_pending_user(username, password_hash):
    """إضافة طلب حساب معلق"""
    try:
        print(f"🔄 بدء إضافة طلب معلق: {username}")
        db = get_db()
        if not db:
            print("❌ فشل في الحصول على قاعدة البيانات")
            return False
            
        # التحقق من عدم وجود المستخدم
        print(f"🔍 التحقق من وجود المستخدم: {username}")
        existing_user = get_user_by_username(username)
        if existing_user:
            print(f"❌ المستخدم موجود بالفعل: {username}")
            return False
            
        # التحقق من عدم وجود طلب معلق
        print(f"🔍 التحقق من وجود طلب معلق: {username}")
        pending_ref = db.collection('pendingUsers')
        
        try:
            existing_pending = pending_ref.where('username', '==', username).stream()
            if list(existing_pending):
                print(f"❌ يوجد طلب معلق بالفعل: {username}")
                return False
        except Exception as e:
            print(f"⚠️ تحذير: مشكلة في الوصول لـ collection pendingUsers: {e}")
            # سنتابع العملية حتى لو كان هناك مشكلة في القراءة
            
        # الحصول على أعلى ID
        print(f"🔢 حساب ID جديد...")
        max_id = 0
        
        try:
            all_pending = pending_ref.stream()
            for pending in all_pending:
                pending_dict = pending.to_dict()
                if 'id' in pending_dict and pending_dict['id'] > max_id:
                    max_id = pending_dict['id']
        except Exception as e:
            print(f"⚠️ تحذير: مشكلة في قراءة الـ IDs الموجودة: {e}")
            print(f"🆔 سيتم استخدام ID افتراضي: 1")
            max_id = 0
        
        new_id = max_id + 1
        print(f"🆔 ID الجديد: {new_id}")
        
        # إضافة الطلب المعلق
        pending_data = {
            'id': new_id,
            'username': username,
            'passwordHash': password_hash,
            'createdAt': datetime.utcnow()
        }
        
        print(f"💾 إضافة البيانات إلى قاعدة البيانات...")
        try:
            doc_ref = pending_ref.add(pending_data)
            print(f"✅ تم إضافة طلب معلق بنجاح: {username}")
            print(f"📄 Document ID: {doc_ref[1].id}")
            return True
        except Exception as add_error:
            print(f"❌ خطأ في إضافة البيانات: {add_error}")
            # محاولة إنشاء collection جديد
            print(f"🔄 محاولة إنشاء collection جديد...")
            try:
                # إضافة document أول لإنشاء collection
                doc_ref = pending_ref.document().set(pending_data)
                print(f"✅ تم إنشاء collection وإضافة الطلب: {username}")
                return True
            except Exception as create_error:
                print(f"❌ فشل في إنشاء collection: {create_error}")
                return False
        
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
        print(f"🔄 بدء رفض المستخدم المعلق: {username}")
        db = get_db()
        if not db:
            print("❌ فشل في الحصول على قاعدة البيانات")
            return False
            
        # البحث عن الطلب المعلق وحذفه
        pending_ref = db.collection('pendingUsers')
        print(f"🔍 البحث عن المستخدم في pendingUsers: {username}")
        
        try:
            pending_query = pending_ref.where('username', '==', username)
            pending_docs = list(pending_query.stream())
            
            if pending_docs:
                for doc in pending_docs:
                    print(f"🗑️ حذف document: {doc.id}")
                    doc.reference.delete()
                print(f"✅ تم رفض المستخدم بنجاح: {username}")
                return True
            else:
                print(f"❌ لم يتم العثور على المستخدم في pendingUsers: {username}")
                return False
                
        except Exception as query_error:
            print(f"❌ خطأ في البحث عن المستخدم: {query_error}")
            return False
        
    except Exception as e:
        print(f"❌ خطأ في رفض المستخدم: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def delete_user(username):
    """حذف مستخدم نهائياً من النظام"""
    try:
        print(f"🔄 بدء حذف المستخدم: {username}")
        db = get_db()
        if not db:
            print("❌ فشل في الحصول على قاعدة البيانات")
            return False
        
        # البحث عن المستخدم وحذفه
        users_ref = db.collection('users')
        print(f"🔍 البحث عن المستخدم في users: {username}")
        
        try:
            user_query = users_ref.where('username', '==', username)
            user_docs = list(user_query.stream())
            
            if user_docs:
                deleted_count = 0
                for doc in user_docs:
                    print(f"🗑️ حذف document: {doc.id}")
                    doc.reference.delete()
                    deleted_count += 1
                
                print(f"✅ تم حذف المستخدم بنجاح: {username} ({deleted_count} documents)")
                
                # حذف طلبات المستخدم أيضاً (اختياري)
                try:
                    requests_ref = db.collection('requests')
                    user_requests = requests_ref.where('employeeId', '==', username).stream()
                    requests_deleted = 0
                    for req_doc in user_requests:
                        req_doc.reference.delete()
                        requests_deleted += 1
                    
                    if requests_deleted > 0:
                        print(f"🗑️ تم حذف {requests_deleted} طلب للمستخدم")
                except Exception as req_error:
                    print(f"⚠️ تحذير: مشكلة في حذف طلبات المستخدم: {req_error}")
                
                return True
            else:
                print(f"❌ لم يتم العثور على المستخدم: {username}")
                return False
                
        except Exception as query_error:
            print(f"❌ خطأ في البحث عن المستخدم: {query_error}")
            return False
        
    except Exception as e:
        print(f"❌ خطأ في حذف المستخدم: {str(e)}")
        import traceback
        traceback.print_exc()
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
            print("❌ قاعدة البيانات غير متصلة")
            return []
            
        print(f"🔍 البحث في collection 'requests' عن آخر {limit} طلبات...")
        requests_ref = db.collection('requests')
        
        # محاولة جلب جميع الوثائق أولاً للتشخيص
        all_docs = list(requests_ref.stream())
        print(f"📊 العدد الكلي للطلبات في Firebase: {len(all_docs)}")
        
        if len(all_docs) == 0:
            print("⚠️ لا توجد طلبات في قاعدة البيانات")
            return []
        
        # جلب الطلبات مرتبة
        try:
            docs = requests_ref.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(limit).stream()
            docs_list = list(docs)
            print(f"📋 تم جلب {len(docs_list)} طلب مرتب")
        except Exception as e:
            print(f"⚠️ خطأ في الترتيب، جلب بدون ترتيب: {e}")
            docs_list = all_docs[:limit]
        
        requests = []
        for i, doc in enumerate(docs_list):
            request_data = doc.to_dict()
            request_data['id'] = doc.id  # إضافة ID للطلب
            
            print(f"   📝 طلب {i+1}: ID={doc.id}, الحالة={request_data.get('status', 'N/A')}, البيانات={list(request_data.keys())}")
            
            # تحويل التواريخ إلى نص
            if 'createdAt' in request_data and request_data['createdAt']:
                if hasattr(request_data['createdAt'], 'strftime'):
                    request_data['created_at'] = request_data['createdAt'].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    request_data['created_at'] = str(request_data['createdAt'])
                    
            if 'executedAt' in request_data and request_data['executedAt']:
                if hasattr(request_data['executedAt'], 'strftime'):
                    request_data['executed_at'] = request_data['executedAt'].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    request_data['executed_at'] = str(request_data['executedAt'])
                    
            if 'canceledAt' in request_data and request_data['canceledAt']:
                if hasattr(request_data['canceledAt'], 'strftime'):
                    request_data['canceled_at'] = request_data['canceledAt'].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    request_data['canceled_at'] = str(request_data['canceledAt'])
            
            # توحيد أسماء الحقول
            if 'employeeId' in request_data:
                request_data['employee_id'] = request_data['employeeId']
            if 'canceledBy' in request_data:
                request_data['canceled_by'] = request_data['canceledBy']
            if 'reqDate' in request_data:
                request_data['date'] = request_data['reqDate']
                
            requests.append(request_data)
            
        print(f"✅ تم إرجاع {len(requests)} طلب بنجاح")
        return requests
        
    except Exception as e:
        print(f"❌ خطأ في جلب الطلبات: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def cancel_request(request_id, canceled_by):
    """إلغاء طلب"""
    try:
        db = get_db()
        if not db:
            return False
            
        # محاولة البحث بـ document ID أولاً
        try:
            doc_ref = db.collection('requests').document(request_id)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({
                    'status': 'canceled',
                    'canceledBy': canceled_by,
                    'canceledAt': datetime.utcnow()
                })
                print(f"✅ تم إلغاء الطلب: {request_id}")
                return True
        except:
            # إذا فشل، جرب البحث بـ integer ID
            pass
            
        # البحث عن الطلب بـ integer ID
        requests_ref = db.collection('requests')
        try:
            query = requests_ref.where('id', '==', int(request_id))
            docs = list(query.stream())
            
            if docs:
                doc_ref = docs[0].reference
                doc_ref.update({
                    'status': 'canceled',
                    'canceledBy': canceled_by,
                    'canceledAt': datetime.utcnow()
                })
                print(f"✅ تم إلغاء الطلب: {request_id}")
                return True
        except ValueError:
            # request_id ليس رقماً
            pass
            
        print(f"❌ لم يتم العثور على الطلب: {request_id}")
        return False
        
    except Exception as e:
        print(f"❌ خطأ في إلغاء الطلب: {str(e)}")
        return False

# === دوال إدارة الموظفين ===

def get_all_employees():
    """جلب جميع الموظفين"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return []
            
        employees_ref = db.collection('employees')
        docs = employees_ref.stream()
        
        employees = []
        for doc in docs:
            employee_data = doc.to_dict()
            employee_data['id'] = doc.id
            employees.append(employee_data)
            
        print(f"✅ تم جلب {len(employees)} موظف")
        return employees
        
    except Exception as e:
        print(f"❌ خطأ في جلب الموظفين: {str(e)}")
        return []

def create_employee(employee_data):
    """إنشاء موظف جديد"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return None
            
        # إضافة البيانات الافتراضية
        employee_data.update({
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'status': 'active'
        })
        
        # التحقق من عدم وجود موظف بنفس الرقم
        existing = db.collection('employees').where('employee_id', '==', employee_data['employee_id']).limit(1).stream()
        if list(existing):
            raise Exception(f"موظف برقم {employee_data['employee_id']} موجود بالفعل")
        
        # إنشاء الموظف
        doc_ref = db.collection('employees').add(employee_data)
        employee_id = doc_ref[1].id
        
        print(f"✅ تم إنشاء الموظف: {employee_data['name']} ({employee_data['employee_id']})")
        return employee_id
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء الموظف: {str(e)}")
        raise e

def get_employee_by_id(employee_id):
    """جلب موظف بالمعرف"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return None
            
        doc_ref = db.collection('employees').document(employee_id)
        doc = doc_ref.get()
        
        if doc.exists:
            employee_data = doc.to_dict()
            employee_data['id'] = doc.id
            return employee_data
        else:
            return None
            
    except Exception as e:
        print(f"❌ خطأ في جلب الموظف: {str(e)}")
        return None

def update_employee(employee_id, update_data):
    """تحديث بيانات موظف"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return False
            
        # إضافة تاريخ التحديث
        update_data['updated_at'] = datetime.utcnow()
        
        doc_ref = db.collection('employees').document(employee_id)
        doc_ref.update(update_data)
        
        print(f"✅ تم تحديث الموظف: {employee_id}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث الموظف: {str(e)}")
        return False

def delete_employee(employee_id):
    """حذف موظف"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return False
            
        doc_ref = db.collection('employees').document(employee_id)
        doc_ref.delete()
        
        print(f"✅ تم حذف الموظف: {employee_id}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في حذف الموظف: {str(e)}")
        return False

def toggle_employee_status(employee_id, active):
    """تفعيل/تعطيل موظف"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return False
            
        status = 'active' if active else 'inactive'
        doc_ref = db.collection('employees').document(employee_id)
        doc_ref.update({
            'status': status,
            'updated_at': datetime.utcnow()
        })
        
        status_text = "تفعيل" if active else "تعطيل"
        print(f"✅ تم {status_text} الموظف: {employee_id}")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تغيير حالة الموظف: {str(e)}")
        return False

def sync_employee_from_attendance(employee_id, name, department):
    """مزامنة بيانات موظف من ملف الحضور"""
    try:
        if not db:
            print("❌ قاعدة البيانات غير متاحة")
            return False
            
        # البحث عن الموظف الموجود
        existing_query = db.collection('employees').where('employee_id', '==', employee_id).limit(1)
        existing_docs = list(existing_query.stream())
        
        if existing_docs:
            # تحديث البيانات الموجودة
            doc_ref = existing_docs[0].reference
            current_data = existing_docs[0].to_dict()
            
            # تحديث الاسم والقسم إذا تغيرا
            updates = {}
            if current_data.get('name') != name:
                updates['name'] = name
            if current_data.get('department') != department:
                updates['department'] = department
                
            if updates:
                updates['updated_at'] = datetime.utcnow()
                updates['synced_from_attendance'] = True
                doc_ref.update(updates)
                print(f"✅ تم تحديث الموظف من ملف الحضور: {employee_id} - {name}")
            
        else:
            # إنشاء موظف جديد
            employee_data = {
                'employee_id': employee_id,
                'name': name,
                'department': department,
                'email': None,
                'phone': None,
                'start_date': None,
                'status': 'active',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'synced_from_attendance': True
            }
            
            db.collection('employees').add(employee_data)
            print(f"✅ تم إنشاء موظف جديد من ملف الحضور: {employee_id} - {name}")
            
        return True
        
    except Exception as e:
        print(f"❌ خطأ في مزامنة الموظف: {str(e)}")
        return False

def sync_employees_batch(employees_data: list) -> dict:
    """
    مزامنة مجموعة من الموظفين مع قاعدة البيانات - محسنة للسرعة
    إرجاع إحصائيات المزامنة
    """
    try:
        db = get_db()
        if not db:
            return {"error": "قاعدة البيانات غير متاحة"}
        
        stats = {
            "total": len(employees_data),
            "created": 0,
            "updated": 0,
            "errors": 0,
            "processed": 0,
            "skipped": 0
        }
        
        print(f"🔄 بدء مزامنة محسنة لـ {len(employees_data)} موظف...")
        
        # جلب جميع الموظفين الموجودين مرة واحدة للمقارنة السريعة
        employees_ref = db.collection('employees')
        existing_employees = {}
        
        try:
            print("📋 جلب الموظفين الموجودين...")
            for doc in employees_ref.stream():
                data = doc.to_dict()
                if 'employee_id' in data:
                    existing_employees[data['employee_id']] = {
                        'doc_ref': doc.reference,
                        'data': data
                    }
            print(f"📊 تم جلب {len(existing_employees)} موظف موجود")
        except Exception as e:
            print(f"⚠️ خطأ في جلب الموظفين الموجودين: {e}")
            # المتابعة بدون التحسين
        
        # معالجة الموظفين
        batch_size = 10  # معالجة دفعية
        for i in range(0, len(employees_data), batch_size):
            batch = employees_data[i:i + batch_size]
            
            for employee in batch:
                try:
                    employee_id = employee.get('EmployeeID')
                    name = employee.get('Name')
                    department = employee.get('Department', 'غير محدد')
                    
                    if not employee_id or not name:
                        stats["errors"] += 1
                        continue
                    
                    # البحث السريع في البيانات المحملة
                    if employee_id in existing_employees:
                        # موظف موجود - تحقق من التحديث
                        existing_data = existing_employees[employee_id]['data']
                        
                        if existing_data.get('name') != name or existing_data.get('department') != department:
                            # تحديث مطلوب
                            doc_ref = existing_employees[employee_id]['doc_ref']
                            doc_ref.update({
                                'name': name,
                                'department': department,
                                'updated_at': datetime.utcnow(),
                                'synced_from_attendance': True
                            })
                            stats["updated"] += 1
                            if stats["updated"] <= 5:  # طباعة أول 5 تحديثات فقط
                                print(f"✅ تم تحديث الموظف: {employee_id} - {name}")
                        else:
                            stats["skipped"] += 1
                    else:
                        # موظف جديد
                        employee_data = {
                            'employee_id': employee_id,
                            'name': name,
                            'department': department,
                            'email': None,
                            'phone': None,
                            'start_date': None,
                            'status': 'active',
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow(),
                            'synced_from_attendance': True
                        }
                        
                        db.collection('employees').add(employee_data)
                        stats["created"] += 1
                        if stats["created"] <= 5:  # طباعة أول 5 إنشاءات فقط
                            print(f"✅ تم إنشاء موظف جديد: {employee_id} - {name}")
                    
                    stats["processed"] += 1
                    
                except Exception as emp_error:
                    print(f"❌ خطأ في معالجة الموظف {employee.get('EmployeeID', 'غير معروف')}: {emp_error}")
                    stats["errors"] += 1
            
            # تقرير التقدم كل دفعة
            progress = ((i + len(batch)) / len(employees_data)) * 100
            print(f"📊 التقدم: {progress:.1f}% ({i + len(batch)}/{len(employees_data)})")
        
        print(f"✅ انتهت المزامنة - إنشاء: {stats['created']}, تحديث: {stats['updated']}, تخطي: {stats['skipped']}, أخطاء: {stats['errors']}")
        return stats
        
    except Exception as e:
        print(f"❌ خطأ في مزامنة الموظفين: {str(e)}")
        return {"error": str(e)}

# تهيئة Firebase عند استيراد الملف
if __name__ != "__main__":
    initialize_firebase()
