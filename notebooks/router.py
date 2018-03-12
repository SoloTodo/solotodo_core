from rest_framework import routers

from notebooks.views import NotebookProcessorViewSet, NotebookVideoCardViewSet

router = routers.SimpleRouter()
router.register(r'notebook_processors', NotebookProcessorViewSet,
                base_name='notebook_processors')
router.register(r'notebook_videocards', NotebookVideoCardViewSet,
                base_name='notebook_video_cards')
