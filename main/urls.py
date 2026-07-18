from django.urls import path
from .views import (register_view, verify_otp_view, resend_otp_view,login_view, 
                    logout_view, parentdashboard,register_child_process, 
                    payment_verify_sandbox,teacherdashboard,
                    parent_submit_assignment, parent_view_submission,
)
from django.conf import settings
from django.conf.urls.static import static
app_name = 'main'

urlpatterns = [
    # مسیرهای احراز هویت
    path('register/', register_view, name='register'),
    path('verify-otp/', verify_otp_view, name='verify_otp'),
    path('resend-otp/', resend_otp_view, name='resend_otp'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
        # مسیرهای داشبورد والدین
    path('dashboard/<str:page>/', parentdashboard, name='dashboard_page'),
    path('dashboard/', parentdashboard, name='parentdashboard'),
    
        # اضافه کردن داشبورد معلم
    path('teacher/<str:page>/', teacherdashboard, name='teacher_page'), 
    path('teacher/', teacherdashboard, name='teacherdashboard'),  
        
    # مسیر پردازش ثبت کودک (جداگانه)
    path('child/register/', register_child_process, name='register_child_process'),
    
    # مسیر تایید پرداخت
    path('payment/verify-sandbox/', payment_verify_sandbox, name='payment_verify_sandbox'),
    # مسیرهای ارسال و مشاهده پاسخ
    path('dashboard/submit/<int:assignment_id>/<int:child_id>/', parent_submit_assignment, name='parent_submit_assignment'),
    path('dashboard/submission/<int:submission_id>/', parent_view_submission, name='parent_view_submission'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)