from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books-database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Bootstrap(app)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    author = db.Column(db.String(250), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    isbn_no = db.Column(db.String, nullable=True)
    pages = db.Column(db.Integer, nullable=True)
    img_url = db.Column(db.String(250), nullable=True)
    language = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f'<Book {self.title}>'

    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary


class ImportBookForm(FlaskForm):
    query = StringField("What do you search for:")
    filter = SelectField("Search in:", choices=["everywhere", "title", "author", "subject", "isbn", "lccn", "oclc"])
    submit = SubmitField("Search")


class AddBook(FlaskForm):
    title = StringField("Book Title", validators=[DataRequired()])
    author = StringField("Author", validators=[DataRequired()])
    year = IntegerField("Publishing year", validators=[DataRequired()])
    isbn_no = StringField("ISBN number", validators=[DataRequired()])
    pages = IntegerField("No. of pages", validators=[DataRequired()])
    img_url = StringField("Cover image", validators=[DataRequired()])
    language = StringField("Language", validators=[DataRequired()])
    submit = SubmitField("Add/Edit Book")


db.create_all()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if request.form['year_from'] == '':
            year_from = 0
        else:
            year_from = int(request.form['year_from'])
        if request.form['year_to'] == '':
            year_to = 3000
        else:
            year_to = int(request.form['year_to'])
        qry = db.session.query(Book)\
            .filter(Book.title.contains(request.form["title"]))\
            .filter(Book.author.contains(request.form["author"]))\
            .filter(Book.language.contains(request.form["lang"]))\
            .filter(Book.year >= year_from)\
            .filter(Book.year <= year_to)\
            .all()
    else:
        qry = Book.query.all()

    return render_template("index.html", books=qry)


@app.route("/search", methods=["GET"])
def search_book():
    title = request.args.get("title")
    author = request.args.get("author")
    lang = request.args.get("lang")
    if request.args.get("from") == '':
        year_from = 0
    else:
        year_from = int(request.args.get("from"))
    if request.args.get("to") == '':
        year_to = 3000
    else:
        year_to = int(request.args.get("to"))
    qry = db.session.query(Book) \
        .filter(Book.title.contains(title)) \
        .filter(Book.author.contains(author)) \
        .filter(Book.language.contains(lang)) \
        .filter(Book.year >= year_from) \
        .filter(Book.year <= year_to) \
        .all()
    if qry:
        qry_book = [book.to_dict() for book in qry]
        return jsonify(book=qry_book)
    else:
        return jsonify(error={"Not Found": "There is no such book in the library"})


@app.route("/add", methods=["GET", "POST"])
def add_book():
    form = AddBook()
    if form.validate_on_submit():
        book_to_update = Book.query.filter_by(title=form.title.data).first()
        if book_to_update:
            book_to_update.author = form.author.data
            book_to_update.year = form.year.data
            book_to_update.isbn_no = form.isbn_no.data
            book_to_update.pages = form.pages.data
            book_to_update.img_url = form.img_url.data
            book_to_update.language = form.language.data
        else:
            new_book = Book(
                title=form.title.data,
                author=form.author.data,
                year=form.year.data,
                isbn_no=form.isbn_no.data,
                pages=form.pages.data,
                img_url=form.img_url.data,
                language=form.language.data
            )
            db.session.add(new_book)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("add.html", form=form)


@app.route("/delete", methods=["GET", "POST"])
def delete_book():
    book_id = request.args.get("book_id")
    book_to_delete = Book.query.get(book_id)
    db.session.delete(book_to_delete)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/import", methods=["GET", "POST"])
def import_book():
    form = ImportBookForm()
    if form.validate_on_submit():
        filter_field = form.filter.data
        text_field = form.query.data
        if filter_field == "everywhere":
            qry = text_field
        elif filter_field == "title":
            qry = f"+intitle:{text_field}"
        elif filter_field == "author":
            qry = f"+inauthor:{text_field}"
        else:
            qry = f"+{filter_field}:{text_field}"

        parameters = {
            "key": "AIzaSyDe7j8Fuk0ffmNDzYPyCOsOhhpKeSnqD2Q",
            "q": qry
        }
        response = requests.get(url="https://www.googleapis.com/books/v1/volumes", params=parameters)
        try:
            books_data = response.json()["items"]
        except KeyError:
            msg = "We cannot find the book. Please try again or change the parameters."
            return render_template("notification.html", msg=msg)
        else:
            return render_template("select.html", books=books_data)
    return render_template("import.html", form=form)


@app.route("/find/<book_id>", methods=["GET", "POST"])
def find_book(book_id):
    response = requests.get(url=f"https://www.googleapis.com/books/v1/volumes/{book_id}",
                            params={"key": "AIzaSyDe7j8Fuk0ffmNDzYPyCOsOhhpKeSnqD2Q"})
    data = response.json()["volumeInfo"]
    for book in Book.query.all():
        if data["title"] == book.title:
            msg = "The book is already in the library."
            return render_template("notification.html", msg=msg)

    book_params = ["title", "authors", "publishedDate", "industryIdentifiers", "pageCount", "imageLinks", "language"]
    book_set = {}
    for item in book_params:
        if item in data:
            book_set[item] = data[item]
        else:
            book_set[item] = ''
    isbn_no = [isbn['identifier'] for isbn in book_set["industryIdentifiers"] if isbn['type'] == 'ISBN_13']
    publish_year = book_set["publishedDate"].split("-")[0]
    if book_set["imageLinks"] != '':
        book_img = book_set["imageLinks"]["smallThumbnail"]
    else:
        book_img = book_set["imageLinks"]

    new_book = Book(
        title=book_set["title"],
        author=book_set["authors"][0],
        year=publish_year,
        isbn_no=isbn_no[0],
        pages=book_set["pageCount"],
        img_url=book_img,
        language=book_set["language"]
    )

    db.session.add(new_book)
    db.session.commit()
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
    # unittest.main()
