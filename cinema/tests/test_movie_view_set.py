from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.test import TestCase

from cinema.models import (
    Movie,
    Genre,
    Actor
)
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
)

MOVIE_URL = reverse("cinema:movie-list")

def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test Movie",
        "description": "Test Movie Description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieTests(TestCase):
    def setUp(self) -> None:
       self.client = APIClient()

    def test_auth_required(self):
       response = self.client.get(MOVIE_URL)
       self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()

        movie_with_genres = sample_movie()
        genre_1 = Genre.objects.create(name="genre1")
        genre_2 = Genre.objects.create(name="genre2")
        movie_with_genres.genres.add(genre_1, genre_2)

        movie_with_actors = sample_movie()
        actor_1 = Actor.objects.create(first_name="test1", last_name="actor1")
        actor_2 = Actor.objects.create(first_name="actor2", last_name="test2")
        movie_with_actors.actors.add(actor_1, actor_2)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="test1")
        movie_with_genre_2 = sample_movie(title="test2")

        genre_1 = Genre.objects.create(name="genre1")
        genre_2 = Genre.objects.create(name="genre2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, response.data)
        self.assertIn(serializer_with_genre_2.data, response.data)
        self.assertNotIn(serializer_without_genre.data, response.data)

    def test_filter_movies_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie(title="test1")
        movie_with_actor_2 = sample_movie(title="test2")

        actor_1 = Actor.objects.create(first_name="test1", last_name="actor1")
        actor_2 = Actor.objects.create(first_name="actor2", last_name="test2")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actor = MovieListSerializer(movie_without_actor)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_with_actor_1.data, response.data)
        self.assertIn(serializer_with_actor_2.data, response.data)
        self.assertNotIn(serializer_without_actor.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="genre1"))
        movie.actors.add(Actor.objects.create(first_name="test1", last_name="actor1"))

        url = movie_detail_url(movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120,
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data.get("id"))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="genre1")
        genre_2 = Genre.objects.create(name="genre2")

        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120,
            "genres": [genre_1.id, genre_2.id],
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data.get("id"))
        genres = movie.genres.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_create_movie_with_actors(self):
        actor_1 = Actor.objects.create(first_name="test1", last_name="actor1")
        actor_2 = Actor.objects.create(first_name="actor2", last_name="test2")

        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120,
            "actors": [actor_1.id, actor_2.id],
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data.get("id"))
        actors = movie.actors.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = movie_detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
