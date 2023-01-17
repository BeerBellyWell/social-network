from http import HTTPStatus
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from posts.models import Post, Group


User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.post = Post.objects.create(
            author=cls.user,
            text='test_post_text',
        )
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_for_all(self):
        """URL для неавторизованных"""
        url_names = {
            '/': HTTPStatus.OK,
            '/group/test_slug/': HTTPStatus.OK,
            '/profile/test_author/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }
        for address, code in url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertEqual(response.status_code, code)

    def test_pages_for_authorized_client(self):
        """URL Страницы доступны авторизованному пользователю."""
        url_names = {
            '/': HTTPStatus.OK,
            '/group/test_slug/': HTTPStatus.OK,
            '/profile/test_author/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            '/create/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/edit/': HTTPStatus.OK,
        }
        for address, code in url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address, follow=True)
                self.assertEqual(response.status_code, code)

    def test_redirect_guest(self):
        """URL Редирект неавторизованных"""
        url_name = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{self.post.pk}/edit/':
            f'/auth/login/?next=/posts/{self.post.pk}/edit/',
            f'/posts/{self.post.pk}/comment/':
            f'/auth/login/?next=/posts/{self.post.pk}/comment/',
        }
        for address, code in url_name.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, code)

    def test_urls_uses_correct_template(self):
        """URL URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            '/profile/test_author/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/post_create.html',
            f'/posts/{self.post.pk}/edit/': 'posts/post_create.html',
            '/unexisting_page/': 'core/404.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address, follow=True)
                self.assertTemplateUsed(response, template)
