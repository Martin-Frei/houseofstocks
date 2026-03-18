from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.



class UserProfile(models.Model):
    """
    Erweitert den Django Standard-User um Mitgliedschaftsstufen.
    
    Stufen (Tiers):
    - free:     Kostenlos, eingeschränkter Zugriff
    - pro:      Bezahlt, voller Zugriff auf GMM + StockPredict
    - premium:  Bezahlt, alles + zukünftige Premium Features
    
    # TODO V2: Stripe Integration für Zahlungsabwicklung
    # TODO V3: AWS als primäres Backend, Supabase als Fallback
    """

    TIER_FREE = 'free'
    TIER_PRO = 'pro'
    TIER_PREMIUM = 'premium'

    TIER_CHOICES = [
        (TIER_FREE, 'Free'),
        (TIER_PRO, 'Pro'),
        (TIER_PREMIUM, 'Premium'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default=TIER_FREE
    )

    # Stripe Customer ID für spätere Zahlungsabwicklung
    # TODO V2: Stripe Webhook füllt dieses Feld automatisch
    stripe_customer_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ─── Hilfsmethoden für Zugriffssteuerung ─────────────────────────────────

    def is_free(self):
        return self.tier == self.TIER_FREE

    def is_pro(self):
        """Pro und Premium haben beide vollen Zugriff."""
        return self.tier in [self.TIER_PRO, self.TIER_PREMIUM]

    def is_premium(self):
        return self.tier == self.TIER_PREMIUM

    def __str__(self):
        return f"{self.user.email} ({self.get_tier_display()})"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


# ─── Signal: UserProfile automatisch anlegen bei neuem User ──────────────────
# Wenn ein neuer User sich registriert, wird automatisch ein
# UserProfile mit Stufe 'free' erstellt – kein manueller Schritt nötig.

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()