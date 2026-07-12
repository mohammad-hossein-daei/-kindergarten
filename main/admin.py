from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    CustomUser, Parent, Employee, ClassRoom, Child, Payment,
    Assignment, Submission, CounselingBooking, Announcement,
    EventRegistration, WeeklyMenu, WeeklyActivity, EmailOTP
)
# ====== ثبت مدل‌ها ======

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'is_active', 'is_staff')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    ordering = ('email',)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'is_active')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    list_filter = ('is_active',)

class EmployeeCreationForm(UserCreationForm):
    class Meta:
        model = Employee
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'role')

class EmployeeChangeForm(UserChangeForm):
    class Meta:
        model = Employee
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'role', 'is_active')
@admin.register(Employee)
class EmployeeAdmin(UserAdmin):  # ✅ تغییر از ModelAdmin به UserAdmin
    form = EmployeeChangeForm
    add_form = EmployeeCreationForm
    
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'role', 'is_active')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    list_filter = ('role', 'is_active')
    ordering = ('email',)
    
    # تنظیم فیلدهای نمایش در فرم ویرایش
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('اطلاعات شغلی', {'fields': ('role',)}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    # تنظیم فیلدهای نمایش در فرم ایجاد
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'phone_number', 'role'),
        }),
    )


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'Capacity', 'Employee')
    search_fields = ('name',)
    list_filter = ('Employee',)

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'birth_date', 'parent', 'classRoom')
    search_fields = ('first_name', 'last_name', 'parent__email')
    list_filter = ('classRoom', 'parent')
    raw_id_fields = ('parent', 'classRoom')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'child', 'amount', 'status', 'date')
    search_fields = ('child__first_name', 'child__last_name', 'description')
    list_filter = ('status', 'date')
    readonly_fields = ('date',)

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_room', 'teacher', 'due_date')
    search_fields = ('title', 'description')
    list_filter = ('class_room', 'teacher', 'due_date')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('child', 'assignment', 'submitted_at')
    search_fields = ('child__first_name', 'child__last_name', 'assignment__title')
    list_filter = ('submitted_at', 'assignment')

@admin.register(CounselingBooking)
class CounselingBookingAdmin(admin.ModelAdmin):
    list_display = ('child', 'counselor', 'date', 'time', 'status')
    search_fields = ('child__first_name', 'child__last_name', 'counselor__email')
    list_filter = ('status', 'date', 'counselor')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'announcement_date', 'is_holiday', 'is_trip')
    search_fields = ('title', 'text')
    list_filter = ('is_holiday', 'is_trip', 'announcement_date')

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('child', 'announcement', 'status', 'note')
    search_fields = ('child__first_name', 'child__last_name', 'announcement__title')
    list_filter = ('status',)

@admin.register(WeeklyMenu)
class WeeklyMenuAdmin(admin.ModelAdmin):
    list_display = ('class_room', 'date', 'meal_type', 'description')
    search_fields = ('description', 'class_room__name')
    list_filter = ('class_room', 'meal_type', 'date')

@admin.register(WeeklyActivity)
class WeeklyActivityAdmin(admin.ModelAdmin):
    list_display = ('class_room', 'day_of_week', 'time_slot', 'activity_name')
    search_fields = ('activity_name', 'class_room__name')
    list_filter = ('class_room', 'day_of_week')

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp_code', 'created_at', 'expires_at', 'is_verified')
    search_fields = ('email', 'otp_code')
    list_filter = ('is_verified', 'created_at')
