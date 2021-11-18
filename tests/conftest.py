import pytest
from main import Book


@pytest.fixture(scope='module')
def new_book():
    book = Book(
        title='Title Test',
        author='Author Test',
        year=2000,
        isbn_no=1313131313131,
        pages=10,
        img_url="https://www.google.com/",
        language="pl"
        )
    return book
