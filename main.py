from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange, URL, ValidationError
import requests
import datetime
import os
from boto.s3.connection import S3Connection


#######################
#### Configuration ####
#######################

conn = S3Connection(os.environ['APP_SECRET_KEY'], os.environ['GOOGLE_BOOKS_API_KEY'])
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('APP_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books-database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Bootstrap(app)


##########################
#### Global variables ####
##########################

TODAY_YEAR = datetime.datetime.today().year


##########################
#### Helper Functions ####
##########################

def length(min_len, max_len):
    message = f'Must include at least {min_len} characters and less than {max_len}'

    def _length(form, field):
        field_len = field.data and len(str(field.data)) or 0
        if field_len < min_len or field_len > max_len:
            raise ValidationError(message)

    return _length


def custom_year(start_year, end_year):
    year = start_year
    if start_year == "":
        year = end_year
    return int(year)


def get_search_data(book_qry):
    title = book_qry.get("title")
    author = book_qry.get("author")
    lang = book_qry.get("lang")
    year_from = custom_year(start_year=book_qry.get("from", 1000), end_year=1000)
    if year_from == "":
        year_from = 1000
    year_to = custom_year(start_year=book_qry.get("to", TODAY_YEAR), end_year=TODAY_YEAR)
    qry = db.session.query(Book)\
        .filter(Book.title.contains(title))\
        .filter(Book.author.contains(author))\
        .filter(Book.language.contains(lang))\
        .filter(Book.year >= year_from)\
        .filter(Book.year <= year_to)\
        .all()
    return qry


#####################
#### Model Class ####
#####################


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    author = db.Column(db.String(100), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    isbn_no = db.Column(db.Integer, nullable=True)
    pages = db.Column(db.Integer, nullable=True)
    img_url = db.Column(db.String(250), nullable=True)
    language = db.Column(db.String(2), nullable=True)

    def __repr__(self):
        return f'<Book {self.title}>'

    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary

    
####################
#### Forms Used ####
####################

class ImportBookForm(FlaskForm):
    query = StringField("What do you search for:", validators=[DataRequired(), length(min_len=1, max_len=50)])
    filter = SelectField("Search in:", choices=["everywhere", "title", "author", "subject", "isbn", "lccn", "oclc"])


class AddBook(FlaskForm):
    title = StringField("Book Title", validators=[DataRequired(), length(min_len=1, max_len=100)])
    author = StringField("Author", validators=[DataRequired(), length(min_len=1, max_len=100)])
    year = IntegerField("Publishing year", validators=[DataRequired(message="Provide numbers"),
                                                       length(min_len=4, max_len=4),
                                                       NumberRange(min=1000, max=TODAY_YEAR)])
    isbn_no = IntegerField("ISBN number", validators=[DataRequired(message="Provide numbers"),
                                                      length(min_len=13, max_len=13),
                                                      NumberRange(min=0)])
    pages = IntegerField("No. of pages", validators=[DataRequired(message="Provide numbers"),
                                                     length(min_len=1, max_len=6),
                                                     NumberRange(min=1, max=100000)])
    img_url = StringField("Cover image", validators=[DataRequired(), URL()])
    language = StringField("Language", validators=[DataRequired(), length(min_len=2, max_len=2)])


#########################
#### Create database ####
#########################

db.create_all()


###################
#### Endpoints ####
###################

@app.route("/")
def home():
    if request.args:
        lib_books = get_search_data(request.args)
    else:
        lib_books = Book.query.all()
    return render_template("index.html", books=lib_books)


@app.route("/search")
def search_book():
    books = get_search_data(request.args)
    if books:
        lib_books = [book.to_dict() for book in books]
        return jsonify(book=lib_books)
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
                title=form.title.data.title(),
                author=form.author.data.title(),
                year=form.year.data,
                isbn_no=form.isbn_no.data,
                pages=form.pages.data,
                img_url=form.img_url.data,
                language=form.language.data.lower()
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
            "key": os.getenv('GOOGLE_BOOKS_API_KEY'),
            "maxResults": 40,
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
                            params={"key": os.getenv('GOOGLE_BOOKS_API_KEY')})
    data = response.json()["volumeInfo"]

    if Book.query.filter_by(title=data["title"]).first():
        msg = "The book is already in the library."
        return render_template("notification.html", msg=msg)
    else:
        if data.get("industryIdentifiers"):
            isbn_no = [isbn.get('identifier') for isbn in data.get("industryIdentifiers") if
                       isbn.get('type') == 'ISBN_13']
        else:
            isbn_no = ['Not found']

        new_book = Book(
            title=data.get("title"),
            author=data.get("authors", [''])[0],
            year=data.get("publishedDate", '').split("-")[0],
            isbn_no=isbn_no[0],
            pages=data.get("pageCount"),
            img_url=data.get("imageLinks", 'No image').get("smallThumbnail", 'No image'),
            language=data.get("language")
        )

        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
