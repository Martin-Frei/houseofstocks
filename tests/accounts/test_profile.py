# tests/accounts/test_profile.py
"""
Tests für UserProfile und das Profil-Signal in accounts/models.py (F-07, F-12).

Ein neuer User bekommt automatisch ein Profil mit Stufe 'free'. F-12: Fehlt das
Profil (User vor der Profil-Migration, gelöschtes Profil, Import), stürzt jedes
Speichern des Users ab – auch der Login, weil er last_login schreibt.
"""
import pytest
from django.contrib.auth.models import User

from accounts.models import UserProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser", email="testuser@example.com", password="test-pass-123"
    )


@pytest.fixture
def user_without_profile(user):
    """User wie vor der Profil-Migration: In der DB gibt es kein Profil.

    Frisch aus der DB laden! Das Objekt `user` hält sein Profil noch im Speicher
    (Django cached die Rückwärtsrelation). Damit träte der Fehler nicht auf,
    und der Test wäre grün aus dem falschen Grund.
    """
    UserProfile.objects.filter(user=user).delete()
    return User.objects.get(pk=user.pk)


# ── Bestehendes Verhalten absichern ────────────────────────────────────────────

def test_new_user_gets_free_profile(user):
    profile = UserProfile.objects.get(user=user)
    assert profile.tier == UserProfile.TIER_FREE


def test_saving_existing_user_keeps_single_profile(user):
    user.first_name = "Test"
    user.save()
    assert UserProfile.objects.filter(user=user).count() == 1


@pytest.mark.parametrize(
    "tier, is_free, is_pro, is_premium",
    [
        (UserProfile.TIER_FREE, True, False, False),
        (UserProfile.TIER_PRO, False, True, False),
        (UserProfile.TIER_PREMIUM, False, True, True),  # Premium hat auch Pro-Zugriff
    ],
)
def test_tier_helpers(user, tier, is_free, is_pro, is_premium):
    profile = user.profile
    profile.tier = tier
    assert profile.is_free() is is_free
    assert profile.is_pro() is is_pro
    assert profile.is_premium() is is_premium


# ── F-12: User ohne Profil ────────────────────────────────────────────────────

def test_saving_user_without_profile_does_not_crash(user_without_profile):
    user_without_profile.save()
    assert UserProfile.objects.filter(user=user_without_profile).exists()


def test_login_of_user_without_profile_does_not_crash(client, user_without_profile):
    # Login schreibt last_login → post_save → Signal.
    client.force_login(user_without_profile)
    assert UserProfile.objects.filter(user=user_without_profile).exists()
    