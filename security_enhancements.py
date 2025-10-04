# تحسينات الأمان لخادم PreStaff
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import bcrypt

# === تشفير كلمات المرور المحسن ===

class PasswordManager:
    """مدير كلمات المرور المحسن"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """تشفير كلمة المرور باستخدام bcrypt"""
        # تحويل كلمة المرور إلى bytes
        password_bytes = password.encode('utf-8')
        
        # إنشاء salt وتشفير كلمة المرور
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds للأمان العالي
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """التحقق من كلمة المرور"""
        try:
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed.encode('utf-8')
            
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """التحقق من قوة كلمة المرور"""
        errors = []
        score = 0
        
        # الطول الأدنى
        if len(password) < 8:
            errors.append('كلمة المرور يجب أن تكون 8 أحرف على الأقل')
        else:
            score += 1
        
        # وجود أحرف كبيرة
        if not re.search(r'[A-Z]', password):
            errors.append('يجب أن تحتوي على حرف كبير واحد على الأقل')
        else:
            score += 1
        
        # وجود أحرف صغيرة
        if not re.search(r'[a-z]', password):
            errors.append('يجب أن تحتوي على حرف صغير واحد على الأقل')
        else:
            score += 1
        
        # وجود أرقام
        if not re.search(r'\d', password):
            errors.append('يجب أن تحتوي على رقم واحد على الأقل')
        else:
            score += 1
        
        # وجود رموز خاصة
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append('يجب أن تحتوي على رمز خاص واحد على الأقل')
        else:
            score += 1
        
        # تقييم القوة
        strength_levels = {
            0: 'ضعيف جداً',
            1: 'ضعيف',
            2: 'متوسط',
            3: 'جيد',
            4: 'قوي',
            5: 'قوي جداً'
        }
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'score': score,
            'strength': strength_levels.get(score, 'غير محدد')
        }

# === إدارة الرموز المميزة المحسنة ===

class TokenManager:
    """مدير الرموز المميزة المحسن"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """إنشاء رمز آمن عشوائي"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def create_jwt_payload(username: str, is_superadmin: bool, services: str) -> Dict[str, Any]:
        """إنشاء payload محسن للـ JWT"""
        now = datetime.utcnow()
        
        return {
            "sub": username,  # subject
            "admin": is_superadmin,
            "srv": services,
            "iat": int(now.timestamp()),  # issued at
            "exp": int((now + timedelta(hours=8)).timestamp()),  # expires in 8 hours
            "jti": TokenManager.generate_secure_token(16),  # JWT ID
            "aud": "prestaff-system",  # audience
            "iss": "prestaff-api"  # issuer
        }

# === تنظيف وتحقق من المدخلات ===

class InputValidator:
    """مُحقق المدخلات"""
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 255) -> str:
        """تنظيف النص من الأحرف الخطيرة"""
        if not text:
            return ""
        
        # إزالة الأحرف الخطيرة
        cleaned = re.sub(r'[<>"\']', '', text.strip())
        
        # تحديد الطول الأقصى
        return cleaned[:max_length]
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """التحقق من صحة اسم المستخدم"""
        errors = []
        
        if not username:
            errors.append('اسم المستخدم مطلوب')
            return {'is_valid': False, 'errors': errors}
        
        # تنظيف اسم المستخدم
        cleaned = InputValidator.sanitize_string(username, 50)
        
        # التحقق من الطول
        if len(cleaned) < 3:
            errors.append('اسم المستخدم يجب أن يكون 3 أحرف على الأقل')
        
        # التحقق من الأحرف المسموحة
        if not re.match(r'^[a-zA-Z0-9._-]+$', cleaned):
            errors.append('اسم المستخدم يجب أن يحتوي على أحرف وأرقام ونقاط وشرطات فقط')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cleaned': cleaned
        }
    
    @staticmethod
    def validate_employee_id(employee_id: str) -> Dict[str, Any]:
        """التحقق من صحة معرف الموظف"""
        errors = []
        
        if not employee_id:
            errors.append('معرف الموظف مطلوب')
            return {'is_valid': False, 'errors': errors}
        
        # تنظيف معرف الموظف
        cleaned = InputValidator.sanitize_string(employee_id, 20)
        
        # التحقق من التنسيق
        if not re.match(r'^[A-Z0-9]+$', cleaned.upper()):
            errors.append('معرف الموظف يجب أن يحتوي على أحرف كبيرة وأرقام فقط')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cleaned': cleaned.upper()
        }

# === مراقبة الأمان ===

class SecurityMonitor:
    """مراقب الأمان"""
    
    def __init__(self):
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.suspicious_activities: List[Dict[str, Any]] = []
    
    def record_failed_login(self, username: str, ip_address: str = "unknown"):
        """تسجيل محاولة دخول فاشلة"""
        now = datetime.utcnow()
        key = f"{username}:{ip_address}"
        
        if key not in self.failed_attempts:
            self.failed_attempts[key] = []
        
        # إضافة المحاولة الحالية
        self.failed_attempts[key].append(now)
        
        # تنظيف المحاولات القديمة (أكثر من ساعة)
        cutoff = now - timedelta(hours=1)
        self.failed_attempts[key] = [
            attempt for attempt in self.failed_attempts[key]
            if attempt > cutoff
        ]
        
        # تسجيل نشاط مشبوه إذا تجاوز الحد
        if len(self.failed_attempts[key]) >= 5:
            self.record_suspicious_activity(
                'multiple_failed_logins',
                f"5+ failed login attempts for {username} from {ip_address}",
                {'username': username, 'ip_address': ip_address, 'attempts': len(self.failed_attempts[key])}
            )
    
    def is_account_locked(self, username: str, ip_address: str = "unknown") -> bool:
        """التحقق من قفل الحساب"""
        key = f"{username}:{ip_address}"
        
        if key in self.failed_attempts:
            # قفل لمدة 30 دقيقة بعد 10 محاولات فاشلة
            recent_attempts = [
                attempt for attempt in self.failed_attempts[key]
                if attempt > datetime.utcnow() - timedelta(minutes=30)
            ]
            return len(recent_attempts) >= 10
        
        return False
    
    def record_suspicious_activity(self, activity_type: str, description: str, metadata: Dict[str, Any] = None):
        """تسجيل نشاط مشبوه"""
        activity = {
            'type': activity_type,
            'description': description,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        self.suspicious_activities.append(activity)
        
        # الاحتفاظ بآخر 100 نشاط فقط
        if len(self.suspicious_activities) > 100:
            self.suspicious_activities = self.suspicious_activities[-100:]
        
        print(f"🚨 نشاط مشبوه: {description}")
    
    def get_security_report(self) -> Dict[str, Any]:
        """جلب تقرير الأمان"""
        now = datetime.utcnow()
        
        # إحصائيات المحاولات الفاشلة
        total_failed_attempts = sum(len(attempts) for attempts in self.failed_attempts.values())
        locked_accounts = sum(
            1 for key in self.failed_attempts.keys()
            if self.is_account_locked(*key.split(':'))
        )
        
        # الأنشطة المشبوهة الأخيرة
        recent_suspicious = [
            activity for activity in self.suspicious_activities
            if datetime.fromisoformat(activity['timestamp']) > now - timedelta(hours=24)
        ]
        
        return {
            'total_failed_attempts': total_failed_attempts,
            'locked_accounts': locked_accounts,
            'recent_suspicious_activities': len(recent_suspicious),
            'suspicious_activities': recent_suspicious[-10:],  # آخر 10 أنشطة
            'timestamp': now.isoformat()
        }

# === إنشاء instances عامة ===

password_manager = PasswordManager()
token_manager = TokenManager()
input_validator = InputValidator()
security_monitor = SecurityMonitor()

# === وظائف مساعدة للأمان ===

def secure_compare(a: str, b: str) -> bool:
    """مقارنة آمنة للنصوص (يمنع timing attacks)"""
    return secrets.compare_digest(a.encode(), b.encode())

def generate_csrf_token() -> str:
    """إنشاء رمز CSRF"""
    return token_manager.generate_secure_token(32)

def validate_request_data(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """التحقق من صحة بيانات الطلب"""
    errors = []
    cleaned_data = {}
    
    for field in required_fields:
        if field not in data:
            errors.append(f'الحقل {field} مطلوب')
        else:
            # تنظيف البيانات حسب نوع الحقل
            if field in ['username']:
                validation = input_validator.validate_username(data[field])
                if validation['is_valid']:
                    cleaned_data[field] = validation['cleaned']
                else:
                    errors.extend(validation['errors'])
            elif field in ['employee_id', 'employeeId']:
                validation = input_validator.validate_employee_id(data[field])
                if validation['is_valid']:
                    cleaned_data[field] = validation['cleaned']
                else:
                    errors.extend(validation['errors'])
            else:
                # تنظيف عام للحقول الأخرى
                cleaned_data[field] = input_validator.sanitize_string(str(data[field]))
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'cleaned_data': cleaned_data
    }

# === تصدير الوظائف ===

__all__ = [
    'PasswordManager',
    'TokenManager', 
    'InputValidator',
    'SecurityMonitor',
    'password_manager',
    'token_manager',
    'input_validator',
    'security_monitor',
    'secure_compare',
    'generate_csrf_token',
    'validate_request_data'
]
