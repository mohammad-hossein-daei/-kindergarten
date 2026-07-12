from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Child,EmailOTP, Submission, Assignment
from django.utils import timezone
User = get_user_model()

class RegisterForm(forms.Form):
    email = forms.EmailField(
        label='ایمیل', 
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=11, 
        label='شماره موبایل',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09123456789'})
    )
    first_name = forms.CharField(
        max_length=150, 
        label='نام', 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150, 
        label='نام خانوادگی', 
        widget=forms.TextInput(attrs={'class': 'form-control'})

    )
    password = forms.CharField(
        label='رمز عبور', 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8
    )
    password_confirm = forms.CharField(
        label='تکرار رمز عبور', 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('این ایمیل قبلاً ثبت شده است')
        return email
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if User.objects.filter(phone_number=phone).exists():
            raise ValidationError('این شماره موبایل قبلاً ثبت شده است')
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError('رمزهای عبور مطابقت ندارند')
        
        return cleaned_data

class VerifyOTPForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6, 
        min_length=6,  # ← اضافه کردن min_length برای اطمینان
        label='کد تأیید',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '123456',
            'maxlength': '6'
        })
    )

class ChildRegistrationForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['first_name', 'last_name', 'birth_date', 'medical_note']
        # classRoom حذف شده چون توسط ادمین تعیین می‌شود
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'medical_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'نکات پزشکی را وارد کنید...'}),
        }
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'birth_date': 'تاریخ تولد',
            'medical_note': 'نکات پزشکی',
        }
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if len(first_name) < 2:
            raise forms.ValidationError('نام باید حداقل ۲ حرف باشد.')
        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if len(last_name) < 2:
            raise forms.ValidationError('نام خانوادگی باید حداقل ۲ حرف باشد.')
        return last_name

class AssignmentForm(forms.ModelForm):
    """
    فرم ارسال تمرین جدید برای یک کلاس
    """
    
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'attachment', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان تمرین را وارد کنید...',
                'dir': 'rtl',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'توضیحات تمرین را وارد کنید...',
                'dir': 'rtl',
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.docx',
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
        }
        labels = {
            'title': 'عنوان تمرین',
            'description': 'توضیحات',
            'attachment': 'فایل ضمیمه (اختیاری)',
            'due_date': 'تاریخ ددلاین',
        }
        help_texts = {
            'attachment': 'فرمت‌های مجاز: PDF، JPG، JPEG، PNG، DOCX',
            'due_date': 'تاریخ و زمان آخرین فرصت برای ارسال پاسخ',
        }
        error_messages = {
            'title': {
                'required': 'عنوان تمرین الزامی است',
            },
            'due_date': {
                'required': 'تاریخ ددلاین الزامی است',
            },
        }
    
    def clean_due_date(self):
        """
        اعتبارسنجی تاریخ ددلاین: نباید در گذشته باشد
        """
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now():
            raise forms.ValidationError('تاریخ ددلاین نمی‌تواند در گذشته باشد')
        return due_date
    
    def clean_title(self):
        """
        اعتبارسنجی عنوان: حذف فضاهای اضافی
        """
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) < 3:
                raise forms.ValidationError('عنوان باید حداقل ۳ کاراکتر باشد')
        return title 
    
class SubmissionForm(forms.ModelForm):
    """
    فرم ارسال پاسخ تمرین توسط والدین
    """
    
    class Meta:
        model = Submission
        fields = ['text_answer', 'attachment']
        widgets = {
            'text_answer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'پاسخ خود را به صورت متن وارد کنید...',
                'dir': 'rtl',
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.docx',
            }),
        }
        labels = {
            'text_answer': 'پاسخ متنی',
            'attachment': 'فایل ضمیمه',
        }
        help_texts = {
            'text_answer': 'می‌توانید پاسخ خود را به صورت متن بنویسید',
            'attachment': 'فرمت‌های مجاز: PDF، JPG، JPEG، PNG، DOCX (حداکثر ۵ مگابایت)',
        }
        error_messages = {
            'text_answer': {
                'required': 'حداقل یکی از فایل یا پاسخ متنی باید ارائه شود',
            },
        }
    
    def clean(self):
        """
        اعتبارسنجی: حداقل یکی از فایل یا پاسخ متنی باید ارائه شود
        """
        cleaned_data = super().clean()
        text_answer = cleaned_data.get('text_answer')
        attachment = cleaned_data.get('attachment')
        
        if not text_answer and not attachment:
            raise forms.ValidationError('حداقل یکی از فایل یا پاسخ متنی باید ارائه شود')
        
        return cleaned_data
    
    def clean_attachment(self):
        """
        اعتبارسنجی حجم فایل
        """
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            max_size = 5 * 1024 * 1024  # 5 MB
            if attachment.size > max_size:
                raise forms.ValidationError(f'حجم فایل نباید بیشتر از {max_size // (1024 * 1024)} مگابایت باشد')
        return attachment