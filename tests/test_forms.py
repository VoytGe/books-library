from unittest import TestCase
from main import ImportBookForm, AddBook
from app import create_app


class ImportBookFormTest(TestCase):
    def test_import_new_book_form(self):
        # Arrange
        app = create_app()
        app.config['WTF_CSRF_ENABLED'] = False

        # Act
        with app.test_request_context('/'):
            form = ImportBookForm()

        # Assert
        self.assertIsInstance(form, ImportBookForm)

    def test_add_book_form(self):
        # Arrange
        app = create_app()
        app.config['WTF_CSRF_ENABLED'] = False

        # Act
        with app.test_request_context('/'):
            form = AddBook()

        # Assert
        self.assertIsInstance(form, AddBook)