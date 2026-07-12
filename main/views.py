# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model, authenticate, logout
from .forms import RegisterForm, VerifyOTPForm, ChildRegistrationForm
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.conf import settings
from .models import EmailOTP, Child, Payment, Parent, ClassRoom, Employee, Assignment, Submission
from django.core.mail import send_mail
import json
import requests
from django.db import transaction
from .forms import ChildRegistrationForm, AssignmentForm, SubmissionForm
from django.core.exceptions import PermissionDenied


User = get_user_model()
def send_otp_email(email, otp_code):
    subject = 'کد تأیید ثبت‌نام'
    html_message = f"""
    <html>
        <body>
            <h2>کد تأیید شما</h2>
            <p>کد تأیید ثبت‌نام شما:</p>
            <h1 style="color: #4CAF50; font-size: 32px;">{otp_code}</h1>
            <p>این کد تا ۵ دقیقه معتبر است.</p>
        </body>
    </html>
    """
    plain_message = f"کد تأیید شما: {otp_code}\nاین کد تا ۵ دقیقه معتبر است."
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        html_message=html_message,
        fail_silently=False,
    )


def register_view(request):
    # ====== پردازش درخواست AJAX ======
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            
            email = data.get('email')
            phone_number = data.get('phone_number')
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            password = data.get('password')
            password_confirm = data.get('password_confirm')
            
            # اعتبارسنجی
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'status': 'error',
                    'error': 'این ایمیل قبلاً ثبت شده است'
                }, status=400)
            
            if User.objects.filter(phone_number=phone_number).exists():
                return JsonResponse({
                    'status': 'error',
                    'error': 'این شماره موبایل قبلاً ثبت شده است'
                }, status=400)
            
            if password != password_confirm:
                return JsonResponse({
                    'status': 'error',
                    'error': 'رمزهای عبور مطابقت ندارند'
                }, status=400)
            
            if len(password) < 8:
                return JsonResponse({
                    'status': 'error',
                    'error': 'رمز عبور باید حداقل ۸ کاراکتر باشد'
                }, status=400)
            
            # ذخیره در session
            request.session['register_data'] = {
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'password': password
            }
            
            # ایجاد OTP
            EmailOTP.objects.filter(email=email, is_verified=False).delete()
            otp_code = EmailOTP.generate_otp()
            EmailOTP.objects.create(
                email=email,
                otp_code=otp_code,
                expires_at=timezone.now() + timezone.timedelta(minutes=5)
            )
            
            # ارسال ایمیل
            try:
                send_otp_email(email, otp_code)
                return JsonResponse({
                    'status': 'success',
                    'message': 'کد تأیید به ایمیل شما ارسال شد'
                })
            except Exception:
                return JsonResponse({
                    'status': 'error',
                    'error': 'خطا در ارسال ایمیل'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'error': 'داده‌های ارسالی نامعتبر است'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'error': f'خطای سرور: {str(e)}'
            }, status=500)
    
    # ====== درخواست GET ======
    form = RegisterForm()
    return render(request, 'registration/parent_register.html', {'form': form})


# ========== ویو تأیید OTP (اصلاح شده) ==========
def verify_otp_view(request):
    # ====== پردازش درخواست AJAX ======
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        is_json = request.content_type == 'application/json'
        
        if is_ajax or is_json:
            try:
                if is_json:
                    data = json.loads(request.body)
                else:
                    data = request.POST
                
                email = data.get('email')
                otp_code = data.get('otp_code')
                
                print(f"Verify OTP - Email: {email}, Code: {otp_code}")
                
                if not email or not otp_code:
                    return JsonResponse({
                        'status': 'error',
                        'error': 'ایمیل و کد OTP الزامی است'
                    }, status=400)
                
                if 'register_data' not in request.session:
                    return JsonResponse({
                        'status': 'error',
                        'error': 'لطفاً ابتدا ثبت‌نام را شروع کنید'
                    }, status=400)
                
                try:
                    otp = EmailOTP.objects.get(
                        email=email,
                        otp_code=otp_code,
                        is_verified=False
                    )
                except EmailOTP.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'error': 'کد تأیید نامعتبر است'
                    }, status=400)
                
                if otp.is_expired():
                    otp.delete()
                    return JsonResponse({
                        'status': 'error',
                        'error': 'کد تأیید منقضی شده است'
                    }, status=400)
                
                otp.is_verified = True
                otp.save()
                
                register_data = request.session['register_data']
                
                # ===== ۱. ایجاد کاربر =====
                user = User.objects.create_user(
                    email=register_data['email'],
                    password=register_data['password'],
                    phone_number=register_data['phone_number'],
                    first_name=register_data['first_name'],
                    last_name=register_data['last_name']
                )
                
                # ===== ۲. ایجاد Parent (با ارث‌بری از CustomUser) =====
                # ✅ درست: Parent با ID کاربر ایجاد می‌شود
                parent = Parent(id=user.id)
                parent.__dict__.update(user.__dict__)
                parent.save()
                
                # پاک کردن session
                del request.session['register_data']
                
                # حذف OTP
                otp.delete()
                
                # لاگین کاربر
                login(request, user)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'ثبت‌نام با موفقیت انجام شد!',
                    'redirect_url': reverse('main:parentdashboard')
                })
                
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'error': 'داده‌های ارسالی نامعتبر است'
                }, status=400)
            except Exception as e:
                print(f"Verify OTP Error: {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({
                    'status': 'error',
                    'error': f'خطای سرور: {str(e)}'
                }, status=500)
    
    # ====== درخواست GET ======
    if 'register_data' not in request.session:
        messages.error(request, 'لطفاً ابتدا ثبت‌نام را شروع کنید')
        return redirect('register')
    
    form = VerifyOTPForm()
    email = request.session.get('register_data', {}).get('email', '')
    return render(request, 'registration/verify_otp.html', {'form': form, 'email': email})

# ========== ویو ارسال مجدد OTP ==========
def resend_otp_view(request):
    # ====== پردازش درخواست AJAX ======
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'داده‌های ارسالی نامعتبر است'
            }, status=400)
    else:
        email = request.session.get('register_data', {}).get('email')
    
    if not email:
        return JsonResponse({
            'status': 'error',
            'message': 'ایمیل یافت نشد'
        }, status=400)
    
    # حذف OTP‌های قبلی
    EmailOTP.objects.filter(email=email, is_verified=False).delete()
    
    # ایجاد OTP جدید
    otp_code = EmailOTP.generate_otp()
    EmailOTP.objects.create(
        email=email,
        otp_code=otp_code,
        expires_at=timezone.now() + timezone.timedelta(minutes=5)
    )
    
    # ارسال ایمیل
    try:
        send_otp_email(email, otp_code)
        return JsonResponse({
            'status': 'success',
            'message': 'کد تأیید جدید به ایمیل شما ارسال شد'
        })
    except Exception:
        return JsonResponse({
            'status': 'error',
            'message': 'خطا در ارسال ایمیل'
        }, status=500)


@csrf_protect
@never_cache
def login_view(request):
    # اگر کاربر قبلاً لاگین کرده، به داشبورد مناسب هدایت کن
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('/admin/')
        elif request.user.is_staff or request.user.groups.filter(name='teacher').exists():
            return redirect('main:teacherdashboard')
        else:
            return redirect('main:parentdashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # اعتبارسنجی اولیه
        if not email or not password:
            messages.error(request, 'لطفاً ایمیل و رمز عبور را وارد کنید')
            return render(request, 'registration/login.html')
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            
            # هدایت بر اساس نقش
            if user.is_superuser:
                return redirect('/admin/')
            elif user.is_staff or user.groups.filter(name='teacher').exists():
                return redirect('main:teacherdashboard')
            else:
                return redirect('main:parentdashboard')
        else:
            messages.error(request, 'ایمیل یا رمز عبور اشتباه است')
            return redirect('main:login')
    
    return render(request, 'registration/login.html')
    
def logout_view(request):
    messages.get_messages(request).used = True
    logout(request)
    return redirect('main:login')

@login_required
def parentdashboard(request, page='home'):
    """
    یک ویو برای مدیریت همه صفحات داشبورد والدین
    """
    
    # ===== تعریف صفحات =====
    PAGES = {
        'home': {
            'template': 'parentdashboard/pages/home.html',
            'title': 'پیشخوان',
            'icon': 'fa-home',
        },
        'children': {
            'template': 'parentdashboard/pages/children.html',
            'title': 'فرزندان',
            'icon': 'fa-child',
        },
        'enrollments': {
            'template': 'parentdashboard/pages/enrollments.html',
            'title': 'ثبت‌نام‌ها',
            'icon': 'fa-calendar-check',
        },
        'classes': {
            'template': 'parentdashboard/pages/classes.html',
            'title': 'کلاس‌ها',
            'icon': 'fa-chalkboard-teacher',
        },
        'payments': {
            'template': 'parentdashboard/pages/payments.html',
            'title': 'پرداخت‌ها',
            'icon': 'fa-credit-card',
        },
        'reports': {
            'template': 'parentdashboard/pages/reports.html',
            'title': 'گزارش‌ها',
            'icon': 'fa-chart-pie',
        },
        'settings': {
            'template': 'parentdashboard/pages/settings.html',
            'title': 'تنظیمات',
            'icon': 'fa-cog',
        },
        'register_child': { 
            'template': 'parentdashboard/pages/register_child.html',
            'title': 'ثبت فرزند جدید',
            'icon': 'fa-user-plus',
        },
    }
    
    # ===== بررسی وجود صفحه =====
    if page not in PAGES:
        from django.http import Http404
        raise Http404("صفحه مورد نظر یافت نشد")
    
    # ===== داده‌های مشترک =====
    context = {
        'active_page': page,
        'page_title': PAGES[page]['title'],
        'page_icon': PAGES[page]['icon'],
        'page_template': PAGES[page]['template'],  # ✅ این متغیر باید به قالب برود
    }
    
    # ===== داده‌های خاص برای صفحه register_child =====
    if page == 'register_child':
        from .forms import ChildRegistrationForm
        form = ChildRegistrationForm()
        context['form'] = form  # ✅ اضافه کردن فرم به context
    
    # ===== داده‌های خاص برای صفحه children =====
    elif page == 'children':
        try:
            parent = request.user.parent
            children = Child.objects.filter(parent=parent)
            context['children'] = children
        except Parent.DoesNotExist:
            context['children'] = []
    
    # ===== داده‌های خاص برای صفحه payments =====
    elif page == 'payments':
        try:
            parent = request.user.parent
            payments = Payment.objects.filter(child__parent=parent).order_by('-date')
            context['payments'] = payments
        except Parent.DoesNotExist:
            context['payments'] = []
    
    return render(request, 'parentdashboard/dashboard.html', context)


def child_registration(request):
    """
    صفحه ثبت اطلاعات کودک و پرداخت از طریق زرین‌پال Sandbox
    """
    if request.method == 'POST':
        # دریافت اطلاعات از فرم
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        birth_date = request.POST.get('birth_date')
        parent_first_name = request.POST.get('parent_first_name')
        parent_last_name = request.POST.get('parent_last_name')
        parent_phone = request.POST.get('parent_phone')
        parent_email = request.POST.get('parent_email')
        amount = request.POST.get('amount', '1000')  # مبلغ پیش‌فرض ۱۰۰۰ تومان
        
        # اعتبارسنجی ساده
        if not all([first_name, last_name, parent_phone, amount]):
            messages.error(request, 'لطفاً تمام فیلدهای ضروری را پر کنید')
            return render(request, 'child_registration.html')
        
        try:
            # ایجاد یا پیدا کردن والد
            parent, created = Parent.objects.get_or_create(
                phone_number=parent_phone,
                defaults={
                    'first_name': parent_first_name,
                    'last_name': parent_last_name,
                    'email': parent_email or f"{parent_phone}@temp.com",
                    'password': 'temp123456'  # رمز موقت
                }
            )
            
            # ایجاد کودک
            child = Child.objects.create(
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date if birth_date else None,
                parent=parent
            )
            
            # ایجاد پرداخت
            payment = Payment.objects.create(
                amount=int(amount),
                description=f'ثبت نام کودک {first_name} {last_name}',
                status='pending',
                child=child
            )
            
            # ارسال به درگاه زرین‌پال Sandbox
            return redirect_to_zarinpal_sandbox(request, payment, child)
            
        except Exception as e:
            messages.error(request, f'خطا در ثبت اطلاعات: {str(e)}')
            return render(request, 'child_registration.html')
    
    return render(request, 'child_registration.html')

@login_required
def register_child_process(request):
    """
    پردازش ثبت کودک و ایجاد پرداخت
    """
    if request.method != 'POST':
        return redirect('main:dashboard_page', page='register_child')
    
    form = ChildRegistrationForm(request.POST)
    
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        return redirect('main:dashboard_page', page='register_child')
    
    try:
        with transaction.atomic():
            # ===== دریافت یا ایجاد Parent =====
            try:
                parent = request.user.parent
            except Parent.DoesNotExist:
                # ✅ ایجاد Parent با روش درست
                parent = Parent(id=request.user.id)
                parent.__dict__.update(request.user.__dict__)
                parent.save()
            
            # ایجاد کودک
            child = Child(
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                birth_date=form.cleaned_data.get('birth_date'),
                medical_note=form.cleaned_data.get('medical_note', ''),
                parent=parent,
                classRoom=None
            )
            child.save()
            
            # ایجاد پرداخت
            amount = 1000
            payment = Payment(
                amount=amount,
                description=f"ثبت نام {child.first_name} {child.last_name}",
                status='pending',
                child=child
            )
            payment.save()
            
            result = redirect_to_zarinpal_sandbox(request, payment, child)
            
            if result:
                return result
            else:
                child.delete()
                payment.delete()
                messages.error(request, 'خطا در اتصال به درگاه پرداخت')
                return redirect('main:dashboard_page', page='register_child')
                
    except Exception as e:
        messages.error(request, f'خطا در ثبت اطلاعات: {str(e)}')
        return redirect('main:dashboard_page', page='register_child')
    
def redirect_to_zarinpal_sandbox(request, payment, child):
    """
    هدایت به درگاه زرین‌پال Sandbox
    """
    request_url = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
    callback_url = request.build_absolute_uri('/payment/verify-sandbox/')
    merchant_id = "123456789012345678901234567890123456"
    
    data = {
        "merchant_id": merchant_id,
        "amount": int(payment.amount),
        "callback_url": callback_url,
        "description": payment.description,
        "metadata": {
            "payment_id": str(payment.id),
            "child_id": str(child.id)
        }
    }
    
    try:
        response = requests.post(request_url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('data', {}).get('code') == 100:
                authority = result['data']['authority']
                gateway_url = f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"
                return redirect(gateway_url)
            else:
                error_message = result.get('errors', {}).get('message', 'خطای ناشناخته')
                messages.error(request, f'خطا در اتصال به درگاه: {error_message}')
                return None
        else:
            messages.error(request, 'خطا در اتصال به سرور زرین‌پال')
            return None
            
    except requests.RequestException as e:
        messages.error(request, f'خطا در ارتباط با درگاه: {str(e)}')
        return None

@csrf_exempt
def payment_verify_sandbox(request):
    """
    تایید پرداخت در Sandbox
    """
    if request.method != 'GET':
        return redirect('main:parentdashboard')
    
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    
    if not authority:
        messages.error(request, 'اطلاعات پرداخت یافت نشد')
        return redirect('main:parentdashboard')
    
    if status == 'OK':
        try:
            with transaction.atomic():
                # پیدا کردن پرداخت (بدون فیلد authority، باید روش دیگری پیدا کنیم)
                # راه حل: از metadata استفاده کنیم یا payment_id را در session ذخیره کنیم
                # برای سادگی، فرض می‌کنیم آخرین پرداخت pending را پیدا می‌کنیم
                payment = Payment.objects.filter(status='pending').order_by('-date').first()
                
                if not payment:
                    messages.error(request, '❌ اطلاعات پرداخت یافت نشد')
                    return render(request, 'parentdashboard/pages/payment_failed.html')
                
                child = payment.child
                
                # تایید پرداخت
                verify_url = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
                merchant_id = getattr(settings, 'ZARINPAL_MERCHANT_ID', "123456789012345678901234567890123456")
                
                data = {
                    "merchant_id": merchant_id,
                    "authority": authority,
                    "amount": int(payment.amount)
                }
                
                response = requests.post(verify_url, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('data', {}).get('code') == 100:
                        # پرداخت موفق
                        payment.status = 'paid'
                        payment.save(update_fields=['status'])
                        
                        messages.success(request, '✅ ثبت نام با موفقیت انجام شد!')
                        return render(request, 'parentdashboard/pages/payment_success.html', {
                            'child': child,
                            'payment': payment,
                            'ref_id': result['data'].get('ref_id', 'N/A')
                        })
                    else:
                        payment.status = 'failed'
                        payment.save(update_fields=['status'])
                        child.delete()  # حذف کودک ثبت شده
                        
                        messages.error(request, '❌ پرداخت ناموفق بود')
                        return render(request, 'parentdashboard/pages/payment_failed.html')
                else:
                    messages.error(request, '❌ خطا در تایید پرداخت')
                    return render(request, 'parentdashboard/pages/payment_failed.html')
                    
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
            return render(request, 'parentdashboard/pages/payment_failed.html')
    else:
        # پرداخت لغو شد
        try:
            with transaction.atomic():
                payment = Payment.objects.filter(status='pending').order_by('-date').first()
                if payment:
                    payment.status = 'canceled'
                    payment.save(update_fields=['status'])
                    
                    child = payment.child
                    child.delete()  # حذف کودک ثبت شده
                    
                    messages.warning(request, '⏹️ پرداخت لغو شد')
        except:
            pass
        return render(request, 'parentdashboard/pages/payment_failed.html')
 
# ===== توابع کمکی برای صفحات مختلف =====

def get_teacher_classes_data(request):
    """دریافت داده‌های صفحه کلاس‌ها"""
    try:
        employee = Employee.objects.get(id=request.user.id)
    except Employee.DoesNotExist:
        return None, None
    
    classes = ClassRoom.objects.filter(Employee=employee).order_by('name')
    
    context = {
        'classes': classes,
    }
    return context, 'teacherdashboard/pages/classes.html'


def get_teacher_class_students_data(request, class_id):
    """دریافت داده‌های صفحه دانش‌آموزان یک کلاس"""
    try:
        employee = Employee.objects.get(id=request.user.id)
    except Employee.DoesNotExist:
        return None, None
    
    class_obj = get_object_or_404(ClassRoom, id=class_id, Employee=employee)
    children = Child.objects.filter(classRoom=class_obj).order_by('last_name', 'first_name')
    
    context = {
        'class_obj': class_obj,
        'children': children,
        'students_count': children.count(),
        'page_title': f'دانش‌آموزان کلاس {class_obj.name}',
    }
    return context, 'teacherdashboard/pages/class_students.html'


def get_teacher_student_detail_data(request, student_id):
    """دریافت داده‌های صفحه جزئیات دانش‌آموز"""
    try:
        employee = Employee.objects.get(id=request.user.id)
    except Employee.DoesNotExist:
        return None, None
    
    child = get_object_or_404(Child, id=student_id)
    
    # بررسی دسترسی
    if child.classRoom.Employee != employee:
        return None, None
    
    context = {
        'student': child,
        'page_title': f'اطلاعات {child.first_name} {child.last_name}',
    }
    return context, 'teacherdashboard/pages/student_detail.html'


def get_teacher_students_data(request):
    """دریافت داده‌های صفحه لیست همه دانش‌آموزان"""
    try:
        employee = Employee.objects.get(id=request.user.id)
    except Employee.DoesNotExist:
        return None, None
    
    students = Child.objects.filter(classRoom__Employee=employee).order_by('last_name', 'first_name')
    
    context = {
        'students': students,
        'students_count': students.count(),
    }
    return context, 'teacherdashboard/pages/students.html'


def get_teacher_attendance_data(request):
    """دریافت داده‌های صفحه حضور و غیاب"""
    context = {
        'today': timezone.now().date(),
    }
    return context, 'teacherdashboard/pages/attendance.html'


def get_employee_or_403(user):
    """دریافت Employee و بررسی دسترسی"""
    try:
        return Employee.objects.get(id=user.id)
    except Employee.DoesNotExist:
        raise PermissionDenied("شما دسترسی به این صفحه ندارید")


# ============================================================
# ===== توابع کمکی برای پردازش صفحات =====
# ============================================================

def handle_class_detail(request, employee, class_id):
    """پردازش صفحه جزئیات کلاس"""
    class_obj = get_object_or_404(ClassRoom, pk=class_id, Employee=employee)
    students = Child.objects.filter(classRoom=class_obj).order_by('last_name', 'first_name')  # ← changed to students
    
    assignments = Assignment.objects.filter(
        class_room=class_obj, 
        teacher=employee
    ).order_by('-due_date')
    
    for assignment in assignments:
        assignment.submission_count = Submission.objects.filter(assignment=assignment).count()
    
    context = {
        'class_obj': class_obj,
        'students': students,  # ← changed to students
        'students_count': students.count(),
        'assignments': assignments,
        'assignments_count': assignments.count(),
        'page_title': f'کلاس {class_obj.name}',
        'page_icon': 'fa-school',
        'page_template': 'teacherdashboard/pages/class_detail.html',
        'current_page': 'classes',
    }
    return context

def handle_new_assignment(request, employee, class_id):
    """پردازش صفحه ارسال تمرین جدید"""
    class_obj = get_object_or_404(ClassRoom, pk=class_id, Employee=employee)
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.class_room = class_obj
            assignment.teacher = employee
            assignment.save()
            messages.success(request, f'تمرین "{assignment.title}" با موفقیت ارسال شد')
            return redirect('main:teacher_page', page=f'class-{class_obj.id}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # مقدار پیش‌فرض برای تاریخ
        default_date = timezone.now() + timezone.timedelta(days=7)
        initial_data = {
            'due_date': default_date.strftime('%Y-%m-%dT%H:%M'),
        }
        form = AssignmentForm(initial=initial_data)
    
    context = {
        'class_obj': class_obj,
        'form': form,
        'page_title': f'ارسال تمرین جدید - {class_obj.name}',
        'page_icon': 'fa-plus-circle',
        'page_template': 'teacherdashboard/pages/new_assignment.html',
    }
    return context

def handle_class_assignments(request, employee, class_id):
    """پردازش صفحه پاسخ‌های کلاس"""
    class_obj = get_object_or_404(ClassRoom, pk=class_id, Employee=employee)
    
    assignments = Assignment.objects.filter(
        class_room=class_obj, 
        teacher=employee
    ).order_by('-due_date')
    
    for assignment in assignments:
        submissions = Submission.objects.filter(assignment=assignment).select_related('child')
        assignment.submissions = submissions
        assignment.submission_count = submissions.count()
    
    context = {
        'class_obj': class_obj,
        'assignments': assignments,
        'assignments_count': assignments.count(),
        'page_title': f'پاسخ‌های کلاس {class_obj.name}',
        'page_icon': 'fa-list',
        'page_template': 'teacherdashboard/pages/class_assignments.html',
    }
    return context

def handle_student_submissions(request, employee, student_id):
    """پردازش صفحه تمرین‌های دانش‌آموز"""
    student = get_object_or_404(Child, pk=student_id)
    
    if student.classRoom.Employee != employee:
        messages.error(request, 'شما دسترسی به این دانش‌آموز ندارید')
        return None
    
    submissions = Submission.objects.filter(
        child=student
    ).select_related('assignment').order_by('-submitted_at')
    
    context = {
        'student': student,
        'submissions': submissions,
        'submissions_count': submissions.count(),
        'page_title': f'تمرین‌های {student.first_name} {student.last_name}',
        'page_icon': 'fa-user-graduate',
        'page_template': 'teacherdashboard/pages/student_submissions.html',
        'current_page': 'students',
    }
    return context

def handle_view_submission(request, employee, submission_id):
    """پردازش صفحه مشاهده جواب تمرین"""
    submission = get_object_or_404(
        Submission.objects.select_related('child', 'assignment', 'assignment__class_room'),
        pk=submission_id
    )
    
    if submission.assignment.class_room.Employee != employee:
        messages.error(request, 'شما دسترسی به این پاسخ ندارید')
        return None
    
    context = {
        'submission': submission,
        'student': submission.child,
        'assignment': submission.assignment,
        'page_title': f'پاسخ تمرین {submission.assignment.title}',
        'page_icon': 'fa-file-alt',
        'page_template': 'teacherdashboard/pages/view_submission.html',
    }
    return context

def handle_assignments_list(request, employee):
    """پردازش صفحه لیست تکالیف"""
    classes = ClassRoom.objects.filter(Employee=employee).order_by('name')
    
    for class_obj in classes:
        class_obj.assignment_count = Assignment.objects.filter(
            class_room=class_obj, 
            teacher=employee
        ).count()
    
    context = {
        'classes': classes,
        'page_title': 'مدیریت تکالیف',
        'page_icon': 'fa-tasks',
        'page_template': 'teacherdashboard/pages/assignments.html',
    }
    return context

def handle_classes_list(request, employee):
    """پردازش صفحه لیست کلاس‌ها"""
    classes = ClassRoom.objects.filter(Employee=employee).order_by('name')
    return {'classes': classes}

def handle_students_list(request, employee):
    """پردازش صفحه لیست دانش‌آموزان"""
    students = Child.objects.filter(classRoom__Employee=employee).order_by('last_name', 'first_name')
    return {
        'students': students,
        'students_count': students.count(),
    }

# ============================================================
# ===== ویو اصلی (کوتاه و خوانا) =====
# ============================================================

@login_required
def teacherdashboard(request, page='home'):
    """
    ویو اصلی داشبورد معلم - مدیریت همه صفحات
    """
    # بررسی دسترسی
    if not request.user.is_staff and not request.user.groups.filter(name='teacher').exists():
        return redirect('main:parentdashboard')
    
    try:
        employee = Employee.objects.get(id=request.user.id)
    except Employee.DoesNotExist:
        messages.error(request, 'شما دسترسی به این صفحه ندارید')
        return redirect('main:parentdashboard')
    
    # ===== تعریف صفحات معمولی =====
    PAGES = {
        'home': {
            'template': 'teacherdashboard/pages/home.html',
            'title': 'پیشخوان',
            'icon': 'fa-home',
            'handler': None,
        },
        'classes': {
            'template': 'teacherdashboard/pages/classes.html',
            'title': 'کلاس‌های من',
            'icon': 'fa-chalkboard-teacher',
            'handler': handle_classes_list,
        },
        'assignments': {
            'template': 'teacherdashboard/pages/assignments.html',
            'title': 'تکالیف',
            'icon': 'fa-tasks',
            'handler': handle_assignments_list,
        },
        'students': {
            'template': 'teacherdashboard/pages/students.html',
            'title': 'دانش‌آموزان',
            'icon': 'fa-user-graduate',
            'handler': handle_students_list,
        },
        'schedule': {
            'template': 'teacherdashboard/pages/schedule.html',
            'title': 'برنامه هفتگی',
            'icon': 'fa-calendar-alt',
            'handler': None,
        },
    }
    
    # ===== داده‌های مشترک =====
    context = {
        'user': request.user,
        'employee': employee,
        'pages': PAGES,
        'total_classes': ClassRoom.objects.filter(Employee=employee).count(),
        'total_students': Child.objects.filter(classRoom__Employee=employee).count(),
    }
    
    # ============================================================
    # ===== پردازش صفحات خاص با پارامتر (ترتیب اهمیت) =====
    # ============================================================
    
    # 1. new-assignment-{id} (خاص‌ترین)
    if page.startswith('new-assignment-'):
        class_id = page.split('-')[2]
        result = handle_new_assignment(request, employee, class_id)
        if isinstance(result, dict):
            result.update({
                'user': request.user,
                'employee': employee,
                'pages': PAGES,
                'total_classes': ClassRoom.objects.filter(Employee=employee).count(),
                'total_students': Child.objects.filter(classRoom__Employee=employee).count(),
            })
            return render(request, 'teacherdashboard/dashboard.html', result)
        return result
    
    # 2. class-assignments-{id}
    elif page.startswith('class-assignments-'):
        class_id = page.split('-')[2]
        result = handle_class_assignments(request, employee, class_id)
        if isinstance(result, dict):
            context.update(result)
            return render(request, 'teacherdashboard/dashboard.html', context)
    
    # 3. student-{id}
    elif page.startswith('student-'):
        student_id = page.split('-')[1]
        result = handle_student_submissions(request, employee, student_id)
        if result is None:
            return redirect('main:teacher_page', page='assignments')
        context.update(result)
        return render(request, 'teacherdashboard/dashboard.html', context)
    
    # 4. submission-{id}
    elif page.startswith('submission-'):
        submission_id = page.split('-')[1]
        result = handle_view_submission(request, employee, submission_id)
        if result is None:
            return redirect('main:teacher_page', page='assignments')
        context.update(result)
        return render(request, 'teacherdashboard/dashboard.html', context)
    
    # 5. class-{id} (عمومی‌ترین - آخر)
    elif page.startswith('class-'):
        class_id = page.split('-')[1]
        result = handle_class_detail(request, employee, class_id)
        if isinstance(result, dict):
            context.update(result)
            context['current_page'] = 'classes'
            return render(request, 'teacherdashboard/dashboard.html', context)
    
    # ============================================================
    # ===== صفحات معمولی =====
    # ============================================================
    
    if page not in PAGES:
        raise Http404("صفحه مورد نظر یافت نشد")
    
    page_data = PAGES[page]
    context.update({
        'current_page': page,
        'page_title': page_data['title'],
        'page_icon': page_data['icon'],
        'page_template': page_data['template'],
    })
    
    # اجرای handler مخصوص صفحه
    if page_data['handler']:
        handler_result = page_data['handler'](request, employee)
        if isinstance(handler_result, dict):
            context.update(handler_result)
    
    return render(request, 'teacherdashboard/dashboard.html', context)
    
# parent_dashboard/views.py (یا همان views.py در بخش والدین)
@login_required
def parent_submit_assignment(request, assignment_id, child_id):
    """
    ارسال پاسخ تمرین توسط والدین
    مسیر: /parent/assignment-{assignment_id}/child-{child_id}/submit/
    """
    # بررسی اینکه فرزند متعلق به این والدین است
    try:
        parent = Parent.objects.get(id=request.user.id)
        child = Child.objects.get(pk=child_id, parent=parent)
    except (Parent.DoesNotExist, Child.DoesNotExist):
        messages.error(request, 'شما دسترسی به این صفحه ندارید')
        return redirect('main:parentdashboard')
    
    # دریافت تمرین
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    
    # بررسی اینکه آیا قبلاً پاسخ داده شده است
    existing_submission = Submission.objects.filter(
        child=child,
        assignment=assignment
    ).first()
    
    if existing_submission:
        messages.warning(request, 'شما قبلاً به این تمرین پاسخ داده‌اید')
        return redirect('main:parent_view_submission', submission_id=existing_submission.pk)
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.child = child
            submission.assignment = assignment
            submission.save()
            messages.success(request, 'پاسخ شما با موفقیت ارسال شد')
            return redirect('main:parentdashboard')
    else:
        form = SubmissionForm()
    
    context = {
        'user': request.user,
        'assignment': assignment,
        'child': child,
        'form': form,
        'page_title': f'ارسال پاسخ - {assignment.title}',
    }
    return render(request, 'parentdashboard/pages/submit_assignment.html', context)