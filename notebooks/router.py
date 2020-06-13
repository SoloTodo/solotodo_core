from rest_framework import routers

from notebooks.views import NotebookProcessorViewSet, NotebookVideoCardViewSet

router = routers.SimpleRouter()
router.register(r'notebook_processors', NotebookProcessorViewSet,
                basename='notebook_processors')
router.register(r'notebook_video_cards', NotebookVideoCardViewSet,
                basename='notebook_video_cards')
