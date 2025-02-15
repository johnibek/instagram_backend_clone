from rest_framework import serializers
from posts.models import Post, PostLike, Comment, CommentLike
from users.models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'photo']


class PostSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)
    post_likes_count = serializers.SerializerMethodField(method_name='get_post_likes_count')
    post_comments_count = serializers.SerializerMethodField(method_name='get_post_comments_count')
    me_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'author', 'image', 'caption', 'created_at', 'post_likes_count', 'post_comments_count', 'me_liked']
        extra_kwargs = {'image': {'required': False}}

    def get_post_likes_count(self, obj):
        return obj.likes.count()

    def get_post_comments_count(self, obj):
        return obj.comments.count()

    def get_me_liked(self, obj):
        # print(self.context)
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            return PostLike.objects.filter(author=request.user, post=obj).exists()

        return False


class CommentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()  # default method name is get_replies()
    me_liked = serializers.SerializerMethodField()  # default method name is get_me_liked()
    comment_likes_count = serializers.SerializerMethodField(method_name='get_likes_count')

    class Meta:
        model = Comment
        fields = ['id', 'author', 'comment_text', 'parent', 'replies', 'me_liked', 'comment_likes_count']


    def get_replies(self, obj):
        if obj.child.exists():
            serializer = self.__class__(obj.child.all(), many=True, context=self.context)  # self.__class__ -> CommentSerializer
            return serializer.data

        return None


    def get_me_liked(self, obj):
        user = self.context.get('request').user

        if user.is_authenticated:
            return obj.likes.filter(author=user).exists()

        return False


    def get_likes_count(self, obj):
        return obj.likes.count()


class PostLikeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = PostLike
        fields = ['id', 'author', 'post']


class CommentLikeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = CommentLike
        fields = ['id', 'author', 'comment']