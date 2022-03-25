from ..media.models import Article
from importly.formatters import (
    Formatted, format_datetime
)

class ArticleDataTransfer:
    class ArticleTransfer:
        model = Article

        external_id = Formatted(str, 'id')

        author = Formatted(str, 'author')
        title = Formatted(str, 'title')
        content = Formatted(str, 'title')

        status = Formatted(str, 'status')

        datetime = Formatted(format_datetime, 'datetime')

        attributions = Formatted(dict, 'attributions')
