# تحسينات الأداء لخادم PreStaff
import functools
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# === تخزين مؤقت بسيط ===

class SimpleCache:
    """تخزين مؤقت بسيط مع انتهاء صلاحية"""
    
    def __init__(self, default_ttl: int = 300):  # 5 دقائق افتراضياً
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """جلب قيمة من التخزين المؤقت"""
        if key in self.cache:
            item = self.cache[key]
            if datetime.utcnow() < item['expires']:
                return item['value']
            else:
                # انتهت الصلاحية، احذف العنصر
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """حفظ قيمة في التخزين المؤقت"""
        ttl = ttl or self.default_ttl
        expires = datetime.utcnow() + timedelta(seconds=ttl)
        self.cache[key] = {
            'value': value,
            'expires': expires
        }
    
    def delete(self, key: str) -> None:
        """حذف قيمة من التخزين المؤقت"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """مسح جميع القيم"""
        self.cache.clear()
    
    def cleanup_expired(self) -> None:
        """تنظيف القيم المنتهية الصلاحية"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, item in self.cache.items()
            if now >= item['expires']
        ]
        for key in expired_keys:
            del self.cache[key]

# إنشاء instance عام للتخزين المؤقت
cache = SimpleCache()

# === Decorators للتحسين ===

def cached(ttl: int = 300, key_func=None):
    """Decorator للتخزين المؤقت للوظائف"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # إنشاء مفتاح فريد
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # محاولة جلب من التخزين المؤقت
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # تنفيذ الوظيفة وحفظ النتيجة
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

def rate_limit(max_calls: int = 10, window: int = 60):
    """Decorator لتحديد معدل الاستدعاءات"""
    calls = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # استخدم IP address كمفتاح (في التطبيق الحقيقي)
            client_id = "global"  # يمكن تحسينه لاستخدام IP
            
            # تنظيف الاستدعاءات القديمة
            if client_id in calls:
                calls[client_id] = [
                    call_time for call_time in calls[client_id]
                    if now - call_time < window
                ]
            else:
                calls[client_id] = []
            
            # تحقق من الحد الأقصى
            if len(calls[client_id]) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {window} seconds")
            
            # إضافة الاستدعاء الحالي
            calls[client_id].append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def timing(func):
    """Decorator لقياس وقت التنفيذ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"⏱️ {func.__name__} took {execution_time:.3f} seconds")
        
        return result
    return wrapper

# === وظائف محسنة لـ Firebase ===

@cached(ttl=180)  # تخزين مؤقت لـ 3 دقائق
@timing
def get_users_cached():
    """جلب المستخدمين مع تخزين مؤقت"""
    from firebase_config import get_all_users
    return get_all_users()

@cached(ttl=60)  # تخزين مؤقت لدقيقة واحدة
@timing
def get_latest_requests_cached(limit=10):
    """جلب أحدث الطلبات مع تخزين مؤقت"""
    from firebase_config import get_latest_requests
    return get_latest_requests(limit)

@rate_limit(max_calls=5, window=60)  # 5 طلبات في الدقيقة
@timing
def create_request_limited(request_data):
    """إنشاء طلب مع تحديد معدل"""
    from firebase_config import create_request
    result = create_request(request_data)
    
    # مسح التخزين المؤقت للطلبات
    cache.delete("get_latest_requests_cached:10")
    
    return result

# === مراقبة الأداء ===

class PerformanceMonitor:
    """مراقب الأداء البسيط"""
    
    def __init__(self):
        self.metrics = {
            'requests_count': 0,
            'total_response_time': 0,
            'errors_count': 0,
            'start_time': datetime.utcnow()
        }
    
    def record_request(self, response_time: float, success: bool = True):
        """تسجيل طلب"""
        self.metrics['requests_count'] += 1
        self.metrics['total_response_time'] += response_time
        
        if not success:
            self.metrics['errors_count'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """جلب الإحصائيات"""
        uptime = datetime.utcnow() - self.metrics['start_time']
        avg_response_time = (
            self.metrics['total_response_time'] / max(self.metrics['requests_count'], 1)
        )
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'total_requests': self.metrics['requests_count'],
            'total_errors': self.metrics['errors_count'],
            'error_rate': self.metrics['errors_count'] / max(self.metrics['requests_count'], 1),
            'average_response_time': avg_response_time,
            'cache_size': len(cache.cache)
        }

# إنشاء instance عام لمراقب الأداء
performance_monitor = PerformanceMonitor()

# === وظائف الصيانة ===

def cleanup_cache():
    """تنظيف التخزين المؤقت"""
    cache.cleanup_expired()
    print(f"🧹 تم تنظيف التخزين المؤقت، العناصر المتبقية: {len(cache.cache)}")

def health_check() -> Dict[str, Any]:
    """فحص صحة النظام"""
    from firebase_config import get_db
    
    try:
        # فحص Firebase
        db = get_db()
        firebase_healthy = db is not None
        
        # فحص التخزين المؤقت
        cache_healthy = len(cache.cache) < 1000  # حد أقصى للأمان
        
        # جلب إحصائيات الأداء
        stats = performance_monitor.get_stats()
        
        return {
            'status': 'healthy' if firebase_healthy and cache_healthy else 'unhealthy',
            'firebase': firebase_healthy,
            'cache': {
                'healthy': cache_healthy,
                'size': len(cache.cache)
            },
            'performance': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

# === تصدير الوظائف ===

__all__ = [
    'cache',
    'cached',
    'rate_limit',
    'timing',
    'get_users_cached',
    'get_latest_requests_cached',
    'create_request_limited',
    'performance_monitor',
    'cleanup_cache',
    'health_check'
]
