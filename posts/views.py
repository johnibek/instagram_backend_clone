from .models import Post, Comment, PostLike, CommentLike
from . import serializers
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from shared.custom_pagination import CustomPagination
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.http import Http404

from .serializers import CommentSerializer, PostLikeSerializer, CommentLikeSerializer


class PostListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = serializers.PostSerializer
    queryset = Post.objects.all()
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Post.objects.all()
    lookup_field='id'

    def put(self, request, *args, **kwargs):
        post = self.get_object()
        serializer = self.serializer_class(instance=post, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'success': True,
                'message': 'Post Successfully updated',
                'data': serializer.data,
            },
            status=status.HTTP_200_OK
        )


    def delete(self, request, *args, **kwargs):
        post = self.get_object()
        post.delete()
        return Response(
            {
                "success": True,
                "message": "You successfully deleted the post"
            },
            status=status.HTTP_204_NO_CONTENT
        )


class CommentListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # print(self.kwargs)  # {'id': UUID('bf219fcf-7177-49fd-a2f4-e3df8b765189')}
        post_id = self.kwargs['id']
        queryset = Comment.objects.filter(post__id=post_id)
        return queryset

    def perform_create(self, serializer):
        post_id = self.kwargs.get('id')
        serializer.save(author=self.request.user, post_id=post_id)


class CommentRetrieveAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        post_id = kwargs['post_id']
        comment_id = kwargs['comment_id']
        try:
            comment = Comment.objects.get(post_id=post_id, id=comment_id)
        except Comment.DoesNotExist:
            raise Http404("Comment with this id does not exist.")
        
        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=200)


class PostLikeListCreateDestroyAPIView(generics.ListCreateAPIView, generics.DestroyAPIView):
    serializer_class = PostLikeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        post_id = self.kwargs.get('id')
        return PostLike.objects.filter(post_id=post_id)

    def post(self, request, *args, **kwargs):
        post_id = kwargs['id']

        try:
            post = PostLike.objects.create(
                author=request.user,
                post_id=post_id
            )
        except Post.DoesNotExist:
            raise Http404("Post with this id does not exist.")
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PostLikeSerializer(post, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)    
    
    def destroy(self, request, *args, **kwargs):
        post_id = kwargs['id']

        try:
            post_like = PostLike.objects.get(post_id=post_id, author=request.user)
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
        
        post_like.delete()
        return Response(
            {
                'success': True,
                'message': 'Post like removed successfully'
            },
            status=status.HTTP_204_NO_CONTENT)


class CommentLikesListCreateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        post_id = kwargs['post_id']
        comment_id = kwargs['comment_id']
        try:
            comment = Comment.objects.get(post_id=post_id, id=comment_id)
            comment_likes = CommentLike.objects.filter(comment=comment)
        except Comment.DoesNotExist:
            raise Http404("Comment with this id does not exist.")
        
        serializer = CommentLikeSerializer(comment_likes, many=True)
        return Response(serializer.data, status=200)
    
    def post(self, request, *args, **kwargs):
        post_id = kwargs['post_id']
        comment_id = kwargs['comment_id']

        try:
            comment_like = CommentLike.objects.create(
                author=request.user,
                comment_id=comment_id
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CommentLikeSerializer(comment_like, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

    def delete(self, request, *args, **kwargs):
        post_id = kwargs['post_id']
        comment_id = kwargs['comment_id']
        
        try:
            comment_like = CommentLike.objects.get(comment_id=comment_id, author=request.user)
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
        
        comment_like.delete()
        return Response(
            {
                'success': True,
                'message': "Comment like removed successfully."
            }, status=status.HTTP_204_NO_CONTENT
        )

