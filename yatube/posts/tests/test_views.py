import shutil
import tempfile

from django.core.cache import cache
from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

from posts.models import Post, Group, Follow
from yatube.settings import NUMBER_OF_PAGES


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='test_author')
        cls.user_sub = User.objects.create_user(username='test_follower')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test_post_text',
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.sub_client = Client()
        self.sub_client.force_login(self.user_sub)

    def check_post(self, first_object):
        self.assertEqual(first_object, self.post)
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author, self.user)
        self.assertEqual(first_object.group, self.group)
        self.assertEqual(first_object.image, self.post.image)

    def test_pages_uses_correct_template(self):
        """VIEWS URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': 'test_slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': 'test_author'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': f'{self.post.pk}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={
                    'post_id': f'{self.post.author.pk}'}
            ): 'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(
                    reverse_name, follow=True)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """INDEX сформирован с правильным контекстом"""
        response = self.client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)

    def test_group_posts_page_show_correct_context(self):
        """GROUP_LIST список постов отфильтрованных по группе"""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test_slug'})
        )
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)
        self.assertEqual(self.group.slug, 'test_slug')
        self.assertEqual(self.group.title, 'test_title')
        self.assertEqual(self.group.description, 'test_description')

    def test_profile_uses_correct_context(self):
        """PROFILE список постов отфильтрованных по пользователю"""
        response = self.client.get(
            reverse(
                'posts:profile',
                kwargs={'username': 'test_author'})
        )
        first_object = response.context['page_obj'][0]
        self.check_post(first_object)
        self.assertEqual(self.group.title, 'test_title')

    def test_post_create_correct_context(self):
        """VIEWS POST_CREATE шаблон сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_correct_context(self):
        """VIEWS POST_EDIT шаблон сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post.author.pk}'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail(self):
        """VIEWS POST_DETAIL один пост, отфильтрованный по id"""
        response = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': f'{self.post.pk}'})
        )
        first_object = response.context.get('post')
        self.check_post(first_object)

    def test_follow(self):
        """Проверка подписки пользователя на автора."""
        self.sub_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user})
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user_sub,
                author=self.user,
            ).exists()
        )

    def test_unfollow(self):
        """Проверка отписки пользователя на автора."""
        count_follow_0 = Follow.objects.all().count()
        self.sub_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user})
        )
        count_follow_1 = Follow.objects.all().count()
        self.sub_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user})
        )
        count_follow_2 = Follow.objects.all().count()
        self.assertNotEqual(count_follow_2, count_follow_1)
        self.assertEqual(count_follow_2, count_follow_0)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user_sub,
                author=self.user,
            ).exists()
        )

    def test_new_follwing_post(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан"""
        Follow.objects.create(user=self.user_sub,
                              author=self.user)
        response = (
            self.sub_client.get(reverse('posts:follow_index'))
        )
        self.assertIn(self.post,
                      response.context.get('page_obj'))

    def test_new_follwing_post(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто не подписан"""
        response = (
            self.sub_client.get(reverse('posts:follow_index'))
        )
        self.assertNotIn(
            self.post,
            response.context.get('page_obj')
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )
        cls.count_posts = 0
        for i in range(11):
            cls.post = Post.objects.create(
                author=cls.user,
                text=f'test_post_text_{i}',
                group=cls.group,
            )
            cls.count_posts += 1
        cls.posts_next_pages = cls.count_posts - NUMBER_OF_PAGES

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_first_page_contains_ten_records(self):
        """VIEWS INDEX количество постов на первой странице равно 10"""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), NUMBER_OF_PAGES)

    def test_index_second_page_contains_one_records(self):
        """VIEWS INDEX на второй странице должно быть 1 пост"""
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), self.posts_next_pages)

    def test_group_list_first_page_contains_ten_records(self):
        """VIEWS GROUP_LIST количество постов на первой странице равно 10"""
        response = self.client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test_slug'})
        )
        self.assertEqual(len(response.context['page_obj']), NUMBER_OF_PAGES)

    def test_group_list_second_page_contains_one_records(self):
        """VIEWS GROUP_LIST количество постов на первой странице равно 1"""
        response = self.client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test_slug'})
            + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), self.posts_next_pages)

    def test_post_profile_first_page_contains_ten_records(self):
        """VIEWS PROFILE список постов отфильтрованных по пользователю
        на первой странице 10"""
        response = self.client.get(reverse(
            'posts:profile',
            kwargs={'username': 'test_author'}
        ))
        self.assertEqual(len(response.context['page_obj']), NUMBER_OF_PAGES)

    def test_post_profile_second_page_contains_one_records(self):
        """VIEWS PROFILE список постов отфильтрованных по пользователю
        на ВТОРОЙ странице 1"""
        response = self.client.get(reverse(
            'posts:profile',
            kwargs={'username': 'test_author'}
        ) + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), self.posts_next_pages)


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_index_cache(self):
        """Тест кеша страницы индекс"""
        response = self.authorized_client.get(reverse('posts:index'))
        before_create_new_post = response.content
        Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        create_new_post = response_2.content
        self.assertEqual(create_new_post, before_create_new_post)

        cache.clear()

        response_3 = self.authorized_client.get(reverse('posts:index'))
        after_cache_clear = response_3.content
        self.assertNotEqual(create_new_post, after_cache_clear)
