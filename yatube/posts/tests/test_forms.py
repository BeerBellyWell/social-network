import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from posts.models import Post, Group, Comment


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_comment_create(self):
        """Валидная форма создает комментарий"""
        self.post = Post.objects.create(
            author=self.user,
            text='test_text',
            group=self.group,
        )
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'comment',
        }
        self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': f'{self.post.pk}'}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='comment',
                post=self.post.pk,
                author=self.user,
            ).exists()
        )

    def test_post_create(self):
        """Валидная форма создает post с картинкой"""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'author': self.user,
            'text': 'test_text',
            'group': self.group.pk,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=self.user,
                text='test_text',
                group=self.group.pk,
                image='posts/small.gif',
            ).exists()
        )

    def test_post_edit(self):
        """Валидная форма редактирует post"""
        self.post = Post.objects.create(
            author=self.user,
            text='test_text',
            group=self.group,
        )
        form_data = {
            'text': 'test_text_edit',
            'group': self.group.pk
        }
        self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post.pk}'}),
            data=form_data,
            follow=True,
        )
        post_edit = Post.objects.get(pk=self.post.pk)
        self.assertEqual(post_edit.text, 'test_text_edit')
        self.assertEqual(post_edit.group.title, self.group.title)
        self.assertEqual(post_edit.author, self.user)
