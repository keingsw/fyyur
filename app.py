#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import sys
import json
import dateutil.parser
import babel
import datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort, session
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
    city_and_state = db.column_property(city + ", " + state)
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
    city_and_state = db.column_property(city + ", " + state)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False, nullable=False)
    seeking_description = db.Column(db.String)
    genres = db.relationship('ArtistGenre', backref='artist', lazy=True)
    shows = db.relationship('Show', cascade='all, delete-orphan', backref='artist', lazy=True)
    available_times = db.relationship('ArtistAvailableTime',
                                      cascade='all, delete-orphan',
                                      backref='artist',
                                      lazy=True)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'id': self.id,
            'name': self.name,
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'image_link': self.image_link,
            'facebook_link': self.facebook_link,
            'website': self.website,
            'seeking_venue': self.seeking_venue,
            'seeking_description': self.seeking_description,
        }


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


class ArtistAvailableTime(db.Model):
    __tablename__ = 'artist_available_times'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_from = db.Column(db.Time, nullable=False)
    time_to = db.Column(db.Time, nullable=False)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'id': self.id,
            'artist_id': self.artist_id,
            'date': self.date.strftime("%Y/%m/%d"),
            'time_from': self.time_from.strftime("%H:%M"),
            'time_to': self.time_to.strftime("%H:%M")
        }


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
    recent_artists = Artist.query.order_by(Artist.id.desc()).limit(10).all()
    recent_venues = Venue.query.order_by(Venue.id.desc()).limit(10).all()
    return render_template('pages/home.html',
                           recent_artists=recent_artists,
                           recent_venues=recent_venues)


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

    query = Venue.query.filter(
        db.or_(Venue.name.ilike('%' + search_term + '%'), Venue.city_and_state == search_term))
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
                  image_link=request.form.get('image_link'),
                  website=request.form.get('website'),
                  facebook_link=request.form.get('facebook_link'),
                  seeking_talent=request.form.get('seeking_talent'),
                  seeking_description=request.form.get('seeking_description'))

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

    query = Artist.query.filter(
        db.or_(Artist.name.ilike('%' + search_term + '%'), Artist.city_and_state == search_term))
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

    return render_template(
        'pages/show_artist.html',
        artist={
            "id":
                artist.id,
            "name":
                artist.name,
            "genres":
                genres,
            "city":
                artist.city,
            "state":
                artist.state,
            "phone":
                artist.phone,
            "website":
                artist.website,
            "facebook_link":
                artist.facebook_link,
            "seeking_venue":
                artist.seeking_venue,
            "seeking_description":
                artist.seeking_description,
            "image_link":
                artist.image_link,
            "past_shows":
                query_past_shows.all(),
            "upcoming_shows":
                query_upcoming_shows.all(),
            "past_shows_count":
                query_past_shows.count(),
            "upcoming_shows_count":
                query_upcoming_shows.count(),
            "available_times": [
                available_time.serialize for available_time in artist.available_times
            ]
        })


@app.route('/artists/<int:artist_id>/available_times')
def get_artist_available_times(artist_id):

    seeking_venue_only = request.args.get('seeking_venue_only')
    response = {'artist': None, 'available_times': []}

    artist = Artist.query.get(artist_id)
    response['artist'] = artist.serialize if artist != None else None

    if artist != None and artist.seeking_venue == True:

        query = ArtistAvailableTime.query.filter(
            ArtistAvailableTime.artist_id == artist_id).order_by(ArtistAvailableTime.date,
                                                                 ArtistAvailableTime.time_from)
        if seeking_venue_only:
            query.join(Artist).filter(Artist.seeking_venue == True)

        response['available_times'] = [available_time.serialize for available_time in query.all()]

    return jsonify(response)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    genres = [artist_genre.genre_name for artist_genre in artist.genres]

    form = ArtistForm()
    form.name.default = artist.name
    form.city.default = artist.city
    form.state.default = artist.state
    form.phone.default = artist.phone
    form.genres.default = genres
    form.image_link.default = artist.image_link
    form.website.default = artist.website
    form.facebook_link.default = artist.facebook_link
    form.seeking_venue.default = artist.seeking_venue
    form.seeking_description.default = artist.seeking_description
    form.process()

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

    error = False

    try:
        input = request.get_json()

        ArtistGenre.query.filter(ArtistGenre.artist_id == artist_id).delete()

        artist = Artist.query.get(artist_id)

        artist.name = input['name']
        artist.city = input['city']
        artist.state = input['state']
        artist.phone = input['phone']
        artist.image_link = input['image_link']
        artist.website = input['website']
        artist.facebook_link = input['facebook_link']
        artist.seeking_venue = input['seeking_venue']
        artist.seeking_description = input['seeking_description']

        for genre_name in input['genres']:
            artist.genres.append(ArtistGenre(genre_name=genre_name))

        for available_time_input in input['available_times']:

            time_from = available_time_input['time_from']
            time_from = '00:00' if time_from == '' else time_from

            time_to = available_time_input['time_to']
            time_to = '23:59' if time_to == '' else time_to

            if 'id' in available_time_input:
                available_time = ArtistAvailableTime.query.get(available_time_input['id'])

                if available_time_input['is_deleted']:
                    db.session.delete(available_time)
                else:
                    available_time.date = available_time_input['date']
                    available_time.time_from = time_from
                    available_time.time_to = time_to
            else:
                artist.available_times.append(
                    ArtistAvailableTime(date=available_time_input['date'],
                                        time_from=time_from,
                                        time_to=time_to))

        db.session.commit()

    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    if error:
        abort(500)
    else:
        return jsonify({"redirect_to": url_for('show_artist', artist_id=artist_id)})


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
                    image_link=request.form.get('image_link'),
                    website=request.form.get('website'),
                    facebook_link=request.form.get('facebook_link'),
                    seeking_venue=request.form.get('seeking_venue') != None,
                    seeking_description=request.form.get('seeking_description'))

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
    subbmited = session.get('create_show')
    form = ShowForm()
    print(subbmited)
    if subbmited:
        form.artist_id.default = subbmited['artist_id']
        form.venue_id.default = subbmited['venue_id']
        form.start_time.default = datetime.strptime(subbmited['start_time'], '%Y-%m-%d %H:%M:%S')
        session.pop('create_show')
    else:
        form.artist_id.default = request.args.get('artist_id')

    form.process()

    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():

    try:
        artist_id = request.form.get('artist_id')
        start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%d %H:%M:%S')

        is_artist_available = ArtistAvailableTime.query.join(Artist).filter(
            Artist.seeking_venue == True, ArtistAvailableTime.artist_id == artist_id,
            ArtistAvailableTime.date == start_time.strftime('%Y-%m-%d'),
            ArtistAvailableTime.time_from <= start_time.strftime('%H:%M:%S'),
            ArtistAvailableTime.time_to >= start_time.strftime('%H:%M:%S')).count() > 0

        if not is_artist_available.count():
            flash('Artist is not available for the `Start Time`.')
            session['create_show'] = request.form
            return redirect(url_for('create_shows'))

        else:
            show = Show(artist_id=artist_id,
                        venue_id=request.form.get('venue_id'),
                        start_time=request.form.get('start_time'))

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
