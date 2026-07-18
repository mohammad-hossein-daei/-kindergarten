from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator, EmailValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import random
import string

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        
        email = self.normalize_email(email)
        
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser, PermissionsMixin):
    username = None
    
    email = models.EmailField(unique=True, blank=False, validators=[EmailValidator()],
                            verbose_name='ایمیل')
    
    phone_regex = RegexValidator(
        regex=r'^09[0-9]{9}$',
        message="شماره موبایل معتبر نیست. باید با 09 شروع شود و 11 رقم باشد. مثال: 09123456789"
    )
    phone_number = models.CharField(max_length=11, validators=[phone_regex],
                                verbose_name='شماره موبایل')
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'custom_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']
    
    def __str__(self):
        return self.email

class Parent(CustomUser):
    class Meta:
        db_table = 'parent'
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'
    
    def __str__(self):
        return self.email

class Employee(CustomUser):
    ROLE_CHOICES = (
        ('teacher', 'مربی'),
        ('counselor', 'مشاور'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='teacher')
    
    class Meta:
        db_table = 'employee'
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
    
    def __str__(self):
        return f"{self.email} - {self.get_role_display()}"

class ClassRoom(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False)
    Capacity = models.PositiveSmallIntegerField(blank=False, null=False)
    Employee = models.ForeignKey("Employee", on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.name} ظرفیت:{self.Capacity}"

class Child(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    birth_date = models.DateField(blank=True, null=True)
    medical_note = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("Parent", on_delete=models.CASCADE)
    classRoom = models.ForeignKey("ClassRoom", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Payment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'در انتظار'),
        ('paid', 'پرداخت شده'),
        ('failed', 'ناموفق'),
        ('canceled', 'لغو شده'),
    )
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default='pending')
    child = models.ForeignKey("Child", on_delete=models.CASCADE)
    
    
    def __str__(self):
        return f"Payment {self.id} - {self.status}"


def file_size_validator(value):
    from django.conf import settings
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
    if value.size > max_size:
        raise ValidationError(f"حداکثر حجم فایل {max_size//(1024*1024)} مگابایت است.")

class Assignment(models.Model):
    title = models.CharField(max_length=200, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    attachment = models.FileField(
        upload_to='report_attachments/%Y/%m/%d/',
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'docx']), file_size_validator],
        verbose_name="ضمیمه"
    )
    due_date = models.DateTimeField(auto_now=False, auto_now_add=False)
    class_room = models.ForeignKey("ClassRoom", on_delete=models.CASCADE)
    teacher = models.ForeignKey("Employee", on_delete=models.CASCADE)
    
    def clean(self):
        if self.due_date and self.due_date < timezone.now():
            raise ValidationError("تاریخ ددلاین نمی‌تواند در گذشته باشد")
    
    def __str__(self):
        class_name = self.class_room.name if self.class_room else "بدون کلاس"
        return f"{self.title} - {self.due_date} - {class_name}"

class Submission(models.Model):
    attachment = models.FileField(
        upload_to='report_attachments/%Y/%m/%d/',
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'docx']), file_size_validator],
        verbose_name="ضمیمه"
    )
    text_answer = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    child = models.ForeignKey("Child", on_delete=models.CASCADE)
    assignment = models.ForeignKey("Assignment", on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['child', 'assignment'], name='unique_submission')
        ]
    
    def clean(self):
        if not self.attachment and not self.text_answer:
            raise ValidationError("حداقل یکی از فایل یا پاسخ متنی باید ارائه شود")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        assignment_title = self.assignment.title if self.assignment else "بدون تکلیف"
        return f"{self.child} - {assignment_title} - {self.submitted_at}"

class CounselingBooking(models.Model):
    REGISTRATION_STATUS = (
        ('pending', 'انتظار'),
        ('confirmed', 'تایید شده'),
        ('canceled', 'لغو شده')
    )
    date = models.DateField(auto_now=False, auto_now_add=False, null=False)
    time = models.TimeField(auto_now=False, auto_now_add=False, null=False)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=REGISTRATION_STATUS, default='pending')
    counselor = models.ForeignKey("Employee", on_delete=models.PROTECT, limit_choices_to={'role': 'counselor'})
    child = models.ForeignKey("Child", on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['date', 'time']
        constraints = [
            models.UniqueConstraint(fields=['counselor', 'date', 'time'], name='unique_counselor_slot')
        ]
    
    def __str__(self):
        return f"{self.child} - {self.counselor} - {self.date} {self.time} - {self.status}"

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    text = models.TextField()
    announcement_date = models.DateTimeField(auto_now_add=True)
    is_holiday = models.BooleanField(default=False)
    is_trip = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'announcement'
        verbose_name = 'اطلاعیه'
        verbose_name_plural = 'اطلاعیه‌ها'
        ordering = ['-announcement_date']
    
    def __str__(self):
        return f"{self.title} - {self.announcement_date.strftime('%Y/%m/%d')}"

class EventRegistration(models.Model):
    REGISTRATION_STATUS = (
        ('pending', 'انتظار'),
        ('confirmed', 'تایید شده'),
        ('canceled', 'لغو شده')
    )
    note = models.TextField(blank=True)
    status = models.CharField(max_length=50, choices=REGISTRATION_STATUS, default='pending')
    announcement = models.ForeignKey("Announcement", on_delete=models.CASCADE)
    child = models.ForeignKey("Child", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.child} - {self.announcement.title} - {self.get_status_display()}"

class WeeklyMenu(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = 'breakfast', 'صبحانه'
        LUNCH = 'lunch', 'ناهار'
        SNACK = 'snack', 'میان‌وعده'
        DINNER = 'dinner', 'شام'
    
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MealType.choices, default=MealType.LUNCH)
    description = models.TextField()
    class_room = models.ForeignKey("ClassRoom", on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'weekly_menu'
        verbose_name = 'منوی هفتگی'
        verbose_name_plural = 'منوهای هفتگی'
        ordering = ['date', 'class_room']
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'meal_type', 'class_room'], 
                name='unique_daily_menu_per_class'
            )
        ]
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.class_room} - {self.date} - {self.get_meal_type_display()}"

class WeeklyActivity(models.Model):
    class DayOfWeek(models.TextChoices):
        SATURDAY = 'saturday', 'شنبه'
        SUNDAY = 'sunday', 'یکشنبه'
        MONDAY = 'monday', 'دوشنبه'
        TUESDAY = 'tuesday', 'سه‌شنبه'
        WEDNESDAY = 'wednesday', 'چهارشنبه'
        THURSDAY = 'thursday', 'پنجشنبه'
    
    class ActivityType(models.TextChoices):
        PAINTING = 'painting', 'نقاشی'
        SPORT = 'sport', 'ورزش'
        MUSIC = 'music', 'موسیقی'
        STORY = 'story', 'قصه‌گویی'
        CRAFT = 'craft', 'کاردستی'
        GAME = 'game', 'بازی گروهی'
        LANGUAGE = 'language', 'آموزش زبان'
        OTHER = 'other', 'سایر'
    
    day_of_week = models.CharField(max_length=20, choices=DayOfWeek.choices)
    time_slot = models.TimeField()
    activity_name = models.CharField(max_length=100)
    class_room = models.ForeignKey("ClassRoom", on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'weekly_activity'
        verbose_name = 'فعالیت هفتگی'
        verbose_name_plural = 'فعالیت‌های هفتگی'
        ordering = ['day_of_week', 'time_slot']
        constraints = [
            models.UniqueConstraint(
                fields=['class_room', 'day_of_week', 'time_slot'], 
                name='unique_class_activity_slot'
            )
        ]
    
    def clean(self):
        if self.time_slot:
            hour = self.time_slot.hour
            if hour < 8 or hour > 17:
                raise ValidationError("زمان فعالیت باید بین ۸ صبح تا ۵ عصر باشد")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.class_room} - {self.get_day_of_week_display()} - {self.time_slot} - {self.activity_name}"
    
    @property
    def day_number(self):
        days = {
            'saturday': 0, 'sunday': 1, 'monday': 2,
            'tuesday': 3, 'wednesday': 4, 'thursday': 5
        }
        return days.get(self.day_of_week, -1)

class EmailOTP(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'email_otp'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {self.otp_code}"
    
    @staticmethod
    def generate_otp():
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        super().save(*args, **kwargs)