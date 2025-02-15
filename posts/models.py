from django.core.validators import FileExtensionValidator, MaxLengthValidator
from django.db import models
from shared.models import BaseModel
from django.contrib.auth import get_user_model
from users.models import CustomUser
from django.db.models.constraints import UniqueConstraint

User = get_user_model()  # Second way to get User

class Post(BaseModel):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts')
    image = models.ImageField(upload_to='post_images', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'tiff', 'heic', 'heif'])])
    caption = models.TextField(validators=[MaxLengthValidator(2000)])

    class Meta:
        db_table = 'posts'
        verbose_name = 'post'
        verbose_name_plural = 'posts'

    def __str__(self):
        return f"Post {self.id} - {self.author.username}"


class Comment(BaseModel):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    comment_text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='child', null=True, blank=True)  # comment1.child.all() gives us all replies to this comment

    def __str__(self):
        return f'Comment by {self.author}'

    """
    "meaning of parent"
    id = 12345
    1) This is beautiful
    parent -> null
    
    id = 123456
    2) What is beautiful?
    parent -> 12345
    """


class PostLike(BaseModel):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['author', 'post'],
                name='PostLike Constraint'
            )
        ]


class CommentLike(BaseModel):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['author', 'comment'],
                name='CommentLike Constraint'
            )
        ]
