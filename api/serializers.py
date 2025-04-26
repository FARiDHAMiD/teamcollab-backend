from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *

# User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

# Sign Up
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'role')

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            # role=validated_data['role']
        )
        return user

# Login
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid credentials")

        tokens = RefreshToken.for_user(user)
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            },
            "tokens": {
                "refresh": str(tokens),
                "access": str(tokens.access_token),
            },
        }
    
# Tokens for blacklist
class TokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()



class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(many=True, read_only=True)
    assigned_to_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'priority', 'assigned_to', 'assigned_to_ids', 'created_by', 'created_at']

    def create(self, validated_data):
        assigned_users = validated_data.pop('assigned_to_ids')
        task = Task.objects.create(**validated_data)
        task.assigned_to.set(assigned_users)
        return task

    def update(self, instance, validated_data):
        if 'assigned_to_ids' in validated_data:
            instance.assigned_to.set(validated_data.pop('assigned_to_ids'))
        return super().update(instance, validated_data)

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    mentions = UserSerializer(many=True, read_only=True)
    mention_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'content', 'mentions', 'mention_ids', 'created_at']

    def create(self, validated_data):
        mentions = validated_data.pop('mention_ids', [])
        comment = Comment.objects.create(**validated_data)
        comment.mentions.set(mentions)
        return comment

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'message', 'url', 'is_read', 'created_at']
