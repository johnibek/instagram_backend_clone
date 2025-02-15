from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'  # http://localhost:8000/posts/?page_size=100
    max_page_size = 100  #  http://localhost:8000/posts/?page_size=100. This amount cannot be greater than 100

    def get_paginated_response(self, data):
        return Response(
            {
                'links': {
                    'previous': self.get_previous_link(),
                    'next': self.get_next_link(),
                },
                'count': self.page.paginator.count,
                'result': data
            }
        )    
