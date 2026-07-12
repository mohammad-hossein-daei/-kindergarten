from django.urls import path
from .views import (register_view, verify_otp_view, resend_otp_view,login_view, 
                    logout_view, parentdashboard,register_child_process, 
                    payment_verify_sandbox,teacherdashboard
)

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
]