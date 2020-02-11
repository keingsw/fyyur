#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import sys
import json
import dateutil.parser
import babel
import datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.String)
    genres = db.relationship('VenueGenre', cascade='all, delete-orphan', backref='venue', lazy=True)
    shows = db.relationship('Show', cascade='all, delete-orphan', backref='venue', lazy=True)


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.String)
    genres = db.relationship('ArtistGenre', backref='artist', lazy=True)
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)


class VenueGenre(db.Model):
    __tablename__ = 'venue_genres'

    id = db.Column(db.Integer, primary_key=True)
    genre_name = db.Column(db.String)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)


class ArtistGenre(db.Model):
    __tablename__ = 'artist_genres'

    id = db.Column(db.Integer, primary_key=True)
    genre_name = db.Column(db.String)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():

    current_time = datetime.now()

    venues = Venue.query.all()
    group_by_city_and_state = {}
    for venue in venues:
        city_and_state = venue.city + '-' + venue.state

        venue.num_upcoming_shows = Show.query.filter(
            Show.venue_id == venue.id,
            Show.start_time > current_time,
        ).count()

        if city_and_state in group_by_city_and_state.keys():
            group_by_city_and_state[city_and_state].venues.append(venue)
        else:
            group_by_city_and_state[city_and_state] = {
                'city': venue.city,
                'state': venue.state,
                'venues': [venue]
            }

    return render_template('pages/venues.html', areas=group_by_city_and_state.values())


@app.route('/venues/search', methods=['POST'])
def search_venues():

    current_time = datetime.now()
    search_term = request.form.get('search_term', '')

    query = Venue.query.filter(Venue.name.ilike('%' + search_term + '%'))
    venues = query.all()

    for venue in venues:
        venue.num_upcoming_shows = Show.query.filter(
            Show.venue_id == venue.id,
            Show.start_time > current_time,
        ).count()

    return render_template('pages/search_venues.html',
                           results={
                               "count": query.count(),
                               "data": venues
                           },
                           search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

    venue = Venue.query.get(venue_id)

    genres = [venue_genre.genre_name for venue_genre in venue.genres]

    current_time = datetime.now()
    query_past_shows = Show.query.join(Artist).with_entities(
        Show.artist_id, Artist.name.label('artist_name'),
        Artist.image_link.label('artist_image_link'),
        Show.start_time).filter(Show.venue_id == venue_id, Show.start_time <= current_time)
    query_upcoming_shows = Show.query.join(Artist).with_entities(
        Show.artist_id, Artist.name.label('artist_name'),
        Artist.image_link.label('artist_image_link'),
        Show.start_time).filter(Show.venue_id == venue_id, Show.start_time > current_time)

    return render_template('pages/show_venue.html',
                           venue={
                               "id": venue.id,
                               "name": venue.name,
                               "genres": genres,
                               "address": venue.address,
                               "city": venue.city,
                               "state": venue.state,
                               "phone": venue.phone,
                               "website": venue.website,
                               "facebook_link": venue.facebook_link,
                               "seeking_talent": venue.seeking_talent,
                               "seeking_description": venue.seeking_description,
                               "image_link": venue.image_link,
                               "past_shows": query_past_shows.all(),
                               "upcoming_shows": query_upcoming_shows.all(),
                               "past_shows_count": query_past_shows.count(),
                               "upcoming_shows_count": query_upcoming_shows.count(),
                           })


#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    venue = Venue(name=request.form.get('name'),
                  city=request.form.get('city'),
                  state=request.form.get('state'),
                  address=request.form.get('address'),
                  phone=request.form.get('phone'),
                  facebook_link=request.form.get('facebook_link'))

    for genre_name in request.form.getlist('genres'):
        venue.genres.append(VenueGenre(genre_name=genre_name))

    try:
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)

    try:
        db.session.delete(venue)
        db.session.commit()
    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    return jsonify({"redirect_to": url_for('index')})


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    return render_template('pages/artists.html', artists=Artist.query.all())


@app.route('/artists/search', methods=['POST'])
def search_artists():

    current_time = datetime.now()
    search_term = request.form.get('search_term', '')

    query = Artist.query.filter(Artist.name.ilike('%' + search_term + '%'))
    artists = query.all()

    for artist in artists:
        artist.num_upcoming_shows = Show.query.filter(Show.artist_id == artist.id,
                                                      Show.start_time > current_time).count()
    return render_template('pages/search_artists.html',
                           results={
                               "count": query.count(),
                               "data": artists
                           },
                           search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

    artist = Artist.query.get(artist_id)

    genres = [artist_genre.genre_name for artist_genre in artist.genres]

    current_time = datetime.now()

    query_past_shows = Show.query.join(Venue).with_entities(
        Show.venue_id, Venue.name.label('venue_name'), Venue.image_link.label('venue_image_link'),
        Show.start_time).filter(Show.artist_id == artist_id, Show.start_time <= current_time)
    query_upcoming_shows = Show.query.join(Venue).with_entities(
        Show.venue_id, Venue.name.label('venue_name'), Venue.image_link.label('venue_image_link'),
        Show.start_time).filter(Show.artist_id == artist_id, Show.start_time > current_time)

    return render_template('pages/show_artist.html',
                           artist={
                               "id": artist.id,
                               "name": artist.name,
                               "genres": genres,
                               "city": artist.city,
                               "state": artist.state,
                               "phone": artist.phone,
                               "website": artist.website,
                               "facebook_link": artist.facebook_link,
                               "seeking_venue": artist.seeking_venue,
                               "seeking_description": artist.seeking_description,
                               "image_link": artist.image_link,
                               "past_shows": query_past_shows.all(),
                               "upcoming_shows": query_upcoming_shows.all(),
                               "past_shows_count": query_past_shows.count(),
                               "upcoming_shows_count": query_upcoming_shows.count()
                           })


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = {
        "id":
            4,
        "name":
            "Guns N Petals",
        "genres": ["Rock n Roll"],
        "city":
            "San Francisco",
        "state":
            "CA",
        "phone":
            "326-123-5000",
        "website":
            "https://www.gunsnpetalsband.com",
        "facebook_link":
            "https://www.facebook.com/GunsNPetals",
        "seeking_venue":
            True,
        "seeking_description":
            "Looking for shows to perform at in the San Francisco Bay Area!",
        "image_link":
            "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
    }
    # TODO: populate form with fields from artist with ID <artist_id>
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    genres = [venue_genre.genre_name for venue_genre in venue.genres]

    form = VenueForm()
    form.name.default = venue.name
    form.city.default = venue.city
    form.state.default = venue.state
    form.address.default = venue.address
    form.phone.default = venue.phone
    form.genres.default = genres
    form.image_link.default = venue.image_link
    form.website.default = venue.website
    form.facebook_link.default = venue.facebook_link
    form.seeking_talent.default = venue.seeking_talent
    form.seeking_description.default = venue.seeking_description
    form.process()

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

    try:
        VenueGenre.query.filter(VenueGenre.venue_id == venue_id).delete()

        venue = Venue.query.get(venue_id)

        is_seeking_talent_checked = request.form.get('seeking_talent') != None
        seeking_talent = is_seeking_talent_checked if venue.seeking_talent != is_seeking_talent_checked else venue.seeking_talent

        venue.name = request.form.get('name', venue.name)
        venue.city = request.form.get('city', venue.city)
        venue.state = request.form.get('state', venue.state)
        venue.phone = request.form.get('phone', venue.phone)
        venue.image_link = request.form.get('image_link', venue.image_link)
        venue.website = request.form.get('website', venue.website)
        venue.facebook_link = request.form.get('facebook_link', venue.facebook_link)
        venue.seeking_talent = seeking_talent
        venue.seeking_description = request.form.get('seeking_description',
                                                     venue.seeking_description)

        for genre_name in request.form.getlist('genres'):
            venue.genres.append(VenueGenre(genre_name=genre_name))

        db.session.commit()

    except:
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    artist = Artist(name=request.form.get('name'),
                    city=request.form.get('city'),
                    state=request.form.get('state'),
                    phone=request.form.get('phone'),
                    facebook_link=request.form.get('facebook_link'))

    for genre_name in request.form.getlist('genres'):
        artist.genres.append(ArtistGenre(genre_name=genre_name))

    try:
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Artist ' + data.name + ' could not be listed.')

    finally:
        db.session.close()

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------


@app.route('/shows')
def shows():

    current_time = datetime.now()

    shows = Show.query.join(Venue).join(Artist).with_entities(
        Show.venue_id, Venue.name.label('venue_name'), Show.artist_id,
        Artist.name.label('artist_name'), Artist.image_link.label('artist_image_link'),
        Show.start_time).filter(Show.start_time > current_time).order_by(Show.start_time).all()

    return render_template('pages/shows.html', shows=shows)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    show = Show(artist_id=request.form.get('artist_id'),
                venue_id=request.form.get('venue_id'),
                start_time=request.form.get('start_time'))

    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        db.session.rollback()
        print(sys.exc_info())
        flash('An error occurred. Show could not be listed.')

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
