def test_new_book_with_fixture(new_book):
    """
    GIVEN a Book model
    WHEN a new Book is created
    THEN check the title, author, year, isbn_no, pages, img_url and language fields are defined correctly
    """
    assert new_book.title == 'Title Test'
    assert new_book.author == "Author Test"
    assert new_book.year == 2000
    assert new_book.isbn_no == 1313131313131
    assert new_book.pages == 10
    assert new_book.img_url == "https://www.google.com/"
    assert new_book.language == "pl"
