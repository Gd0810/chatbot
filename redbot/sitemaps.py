from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from bots.models import Bot

class BotSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Bot.objects.filter(is_enabled=True)

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return ['index', 'service', 'contact', 'about', 'aibot', 'livebot', 'faqbot']

    def location(self, item):
        return reverse(item)