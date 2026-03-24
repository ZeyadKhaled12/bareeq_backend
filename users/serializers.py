import re
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile, TimeSlot
from lists.models import Gender

User = get_user_model()

# --- AUTHENTICATION SERIALIZERS ---
# users/serializers.py


class VendorTimeSlotSerializer(serializers.ModelSerializer):
    """Serializer for managing individual time slots"""
    class Meta:
        model = TimeSlot
        fields = [
            'id', 'day', 'slot', 'slot_type',
            'is_free', 'unlimit_orders', 'limit_orders', 'is_close'
        ]


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        required=True,
        validators=[UniqueValidator(
            queryset=User.objects.all(), message="هذا الاسم مستخدم بالفعل")]
    )
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(
        ), message="هذا البريد الإلكتروني مسجل مسبقاً")]
    )
    password = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(
        write_only=True,
        required=True,
        validators=[UniqueValidator(
            queryset=UserProfile.objects.all(), message="رقم الهاتف هذا مسجل مسبقاً")]
    )
    gender = serializers.PrimaryKeyRelatedField(
        queryset=Gender.objects.all(), write_only=True, required=True)
    date_of_birth = serializers.DateField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email',
                  'phone', 'gender', 'date_of_birth']

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_phone(self, value):
        if not re.match(r'^(010|011|012|015)\d{8}$', value):
            raise serializers.ValidationError(
                "رقم الهاتف غير صحيح. يجب أن يبدأ بـ 010 أو 011 أو 012 أو 015")
        return value

    def create(self, validated_data):
        phone = validated_data.pop('phone')
        gender = validated_data.pop('gender')
        dob = validated_data.pop('date_of_birth')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        UserProfile.objects.create(
            user=user,
            role='CUSTOMER',
            phone=phone,
            gender=gender,
            date_of_birth=dob
        )
        return user

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        profile = getattr(instance, 'profile', None)
        if profile:
            representation['phone'] = profile.phone
            representation['gender'] = profile.gender.id if profile.gender else None
            representation['date_of_birth'] = profile.date_of_birth
            representation['role'] = profile.role
        return representation


class LoginSerializer(serializers.Serializer):
    """Handles login for Shop Owners (Vendors) and Staff (Employees)"""
    login_id = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        login_id = data.get('login_id')
        password = data.get('password')

        user = User.objects.filter(
            Q(email=login_id) | Q(profile__phone=login_id)
        ).select_related('profile').first()

        if user and user.check_password(password):
            if not user.is_active:
                raise serializers.ValidationError("هذا الحساب معطل.")

            try:
                profile = user.profile
            except UserProfile.DoesNotExist:
                raise serializers.ValidationError(
                    f"المستخدم {user.username} ليس لديه ملف شخصي.")

            role = profile.role.upper()
            if role not in ['VENDOR', 'EMPLOYEE']:
                raise serializers.ValidationError(
                    "هذا الرابط مخصص للمحلات والموظفين فقط.")

            return user
        raise serializers.ValidationError("بيانات الدخول غير صحيحة.")


class CustomerLoginSerializer(serializers.Serializer):
    """Handles login specifically for Customers"""
    login_id = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        login_id = data.get('login_id')
        password = data.get('password')

        user = User.objects.filter(
            Q(email=login_id) | Q(profile__phone=login_id)
        ).select_related('profile').first()

        if user and user.check_password(password):
            if not user.is_active:
                raise serializers.ValidationError("هذا الحساب معطل.")

            if not hasattr(user, 'profile') or user.profile.role.upper() != 'CUSTOMER':
                raise serializers.ValidationError(
                    "هذا الرابط مخصص للعملاء فقط.")

            return user
        raise serializers.ValidationError("بيانات الدخول غير صحيحة.")


# --- VENDOR & EMPLOYEE MANAGEMENT SERIALIZERS ---

class VendorRegisterSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source='username', required=True)
    full_name = serializers.CharField(source='first_name', required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['phone', 'email', 'full_name', 'password']

    def validate_phone(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("هذا الرقم مسجل مسبقاً")
        if not re.match(r'^01[0125][0-9]{8}$', value):
            raise serializers.ValidationError("يرجى إدخال رقم هاتف مصري صحيح")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name']
        )
        UserProfile.objects.create(
            user=user, role='VENDOR', phone=validated_data['username'])
        return user

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            'user': {
                'full_name': instance.first_name,
                'email': instance.email,
                'phone': instance.profile.phone,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


class EmployeeCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    full_name = serializers.CharField(source='user.first_name')
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ['email', 'password', 'full_name', 'phone']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("هذا البريد مسجل مسبقاً.")
        return value

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        email = user_data.get('email')
        full_name = user_data.get('first_name')
        password = validated_data.pop('password')
        phone = validated_data.get('phone', '')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name
        )

        vendor_profile = self.context['request'].user.profile
        profile = UserProfile.objects.create(
            user=user,
            role='EMPLOYEE',
            employer=vendor_profile,
            phone=phone
        )
        return profile


# --- PROFILE & UTILITY SERIALIZERS ---

class UserProfileSerializer(serializers.ModelSerializer):
    """Missing class fixed here"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email',
                  'full_name', 'phone', 'role', 'employer']


class VendorProfileSerializer(serializers.ModelSerializer):
    """Missing class fixed here"""
    phone = serializers.CharField(source='username')
    full_name = serializers.CharField(source='first_name')

    class Meta:
        model = User
        fields = ['phone', 'email', 'full_name']

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get(
            'first_name', instance.first_name)
        instance.save()

        profile = instance.profile
        profile.phone = instance.username
        profile.save()
        return instance


class CustomerUpdateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source='profile.phone')
    gender = serializers.PrimaryKeyRelatedField(
        source='profile.gender', queryset=Gender.objects.all())
    date_of_birth = serializers.DateField(source='profile.date_of_birth')

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'gender', 'date_of_birth']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.save()

        profile = instance.profile
        profile.phone = profile_data.get('phone', profile.phone)
        profile.gender = profile_data.get('gender', profile.gender)
        profile.date_of_birth = profile_data.get(
            'date_of_birth', profile.date_of_birth)
        profile.save()
        return instance

    def to_representation(self, instance):
        return CustomerRegistrationSerializer(instance).data


class VendorAuthResponseSerializer(serializers.Serializer):
    class UserDataSerializer(serializers.Serializer):
        full_name = serializers.CharField()
        email = serializers.EmailField()
        phone = serializers.CharField()
        role = serializers.CharField()

    user = UserDataSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password": "كلمات المرور الجديدة غير متطابقة"})
        return data


# --- TIME SLOT SERIALIZERS ---

class TimeSlotItemSerializer(serializers.ModelSerializer):
    is_full = serializers.SerializerMethodField()

    class Meta:
        model = TimeSlot
        fields = ['id', 'slot', 'is_free', 'unlimit_orders',
                  'limit_orders', 'is_close', 'is_full']

    def get_is_full(self, obj):
        target_date = self.context.get('target_date')
        if not target_date or obj.unlimit_orders:
            return False
        count = obj.orders.filter(pickup_date=target_date).count()
        return count >= obj.limit_orders


class VendorTimeSlotResponseSerializer(serializers.Serializer):
    def to_representation(self, instance):
        days = ['monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday']
        response = {}
        for day in days:
            response[day] = {
                "receipt": TimeSlotItemSerializer(instance.time_slots.filter(day=day, slot_type='receipt'), many=True).data,
                "delivery": TimeSlotItemSerializer(instance.time_slots.filter(day=day, slot_type='delivery'), many=True).data,
            }
        return response

# users/serializers.py


class DaySlotsSerializer(serializers.Serializer):
    receipt = TimeSlotItemSerializer(many=True, required=False)
    delivery = TimeSlotItemSerializer(many=True, required=False)


class TimeSlotBulkUpdateSerializer(serializers.Serializer):
    """Serializer for updating multiple time slots at once"""
    monday = DaySlotsSerializer(required=False)
    tuesday = DaySlotsSerializer(required=False)
    wednesday = DaySlotsSerializer(required=False)
    thursday = DaySlotsSerializer(required=False)
    friday = DaySlotsSerializer(required=False)
    saturday = DaySlotsSerializer(required=False)
    sunday = DaySlotsSerializer(required=False)

    def update_slots(self, vendor_profile):
        slots_data = self.validated_data.get('slots', [])
        updated_slots = []

        for slot_data in slots_data:
            slot_id = slot_data.get('id')
            if slot_id:
                # Ensure the slot belongs to this vendor for security
                slot = TimeSlot.objects.filter(
                    id=slot_id, vendor=vendor_profile).first()
                if slot:
                    for attr, value in slot_data.items():
                        if attr != 'id':
                            setattr(slot, attr, value)
                    slot.save()
                    updated_slots.append(slot)
        return updated_slots
