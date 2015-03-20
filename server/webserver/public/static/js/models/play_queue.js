var PlayQueue = Backbone.Model.extend({
  defaults: function () {
    return {
      songs: new SongCollection(),
      current: undefined,
      currently_playing_song: undefined,
      shuffle: false,
      repeat: false
    }
  },
  add_next: function(song) {
    var songs = this.get('songs');
    var curr = this.get('current');
    if (curr === undefined) {
      curr = -1;
    }
    songs.add(song, {at: curr + 1});
    if (song.length > 0) {
      for (var s in song) {
        var sng = song[s];
        sng.download();
      }
    } else {
      song.download();
    }
  },
  add_last: function(song) {
    var songs = this.get('songs');
    songs.add(song);
    if (song.length > 0) {
      for (var s in song) {
        var sng = song[s];
        sng.download();
      }
    } else {
      song.download();
    }
  },
  play_song: function (id) {
    // force the event
    this.set('current', id, {silent: true});
    this.trigger('change');
    this.trigger('change:current');
  },
  play_prev: function () {
    var curr = this.get('current');
    if (curr !== undefined) {
      if (curr > 0) {
        this.set('current', curr - 1);
      } else {
        this.set('current', undefined)
      }
    }
  },
  play_next: function() {
    var shuffle = this.get('shuffle');
    var repeat = this.get('repeat');
    var current = this.get('current');
    var length = this.get('songs').length;
    var last = length - 1;
    if (last == -1) {
      this.play_song(undefined);
      return;
    }

    // first make sure at least one other song is playable
    var songs = this.get('songs').models;
    var found = 0;
    for (var s in songs) {
      var song = songs[s];
      if (song.get('percent-dl') > 0) {
        found += 1;
      }
    }
    if (!(found > 1 || (current === undefined && found > 0))) {
      return;
    }

    // dumb shuffle (completely random)
    if (shuffle && length > 1) {
      while (true) {
        var rand_id = Math.floor(Math.random() * (length - 1));
        if (rand_id >= current) {
          rand_id++;
        }
        // we already know at least one song is playable so we know
        // this will execute at least once eventually
        if (this.get('songs').at(rand_id).get('percent-dl') > 0) {
          break;
        }
      }
      this.play_song(rand_id);
    } else {
      var next = current;
      while (true) {
        if (next === undefined) {
          next = 0;
          break;
        } else if (repeat) {
          next = (next + 1) % length;
        } else {
          next = next + 1;
          if (next == length) {
            next = undefined;
            //TODO: this shouldn't be here. This is really hacky. I'm not sure what bug it fixes,
            // but this not okay
            this.set('current', undefined);
            this.set('currently_playing_song', undefined);
            break;
          }
        }
        // we already know at least one song is playable so we know
        // this will execute at least once eventually
        if (this.get('songs').at(next).get('percent-dl') > 0) {
          break;
        }
      }
      // move the song up in the list if it's from the future
      if (next > current+1) {
        this.move_from_to(next, current+1);
        next = current+1;
      } else if (current != last && next < current) {
        this.move_from_to(next, current);
        next = current;
      }
      this.play_song(next);
    }
  },
  current_song: function() {
    var curr = this.get('current');
    if (curr !== undefined) {
      return this.get('songs').at(curr);
    } else {
      return undefined;
    }
  },
  move_song_up: function(id) {
    
    if (id === 0) {
      return;
    }
    
    var songs = this.get('songs');
    var curr = this.get('current');
    
    songs.swap(id, id-1);
    
    if (id === curr) {
      this.set('current', id-1);
    } else if (id-1 === curr) {
      this.set('current', id);
    }
  },
  move_song_down: function(id) {
    var songs = this.get('songs');

    if (id === songs.length - 1) {
      return;
    }

    var curr = this.get('current');
    
    songs.swap(id, id+1);
    
    if (id === curr) {
      this.set('current', id+1);
    } else if (id+1 === curr) {
      this.set('current', id);
    }
  },
  remove_song: function(id) {
    var songs = this.get('songs');
    var curr = this.get('current');
    
    if (curr >= id) {
      this.set('current', curr-1, {silent:true});
    }
   
    songs.remove(songs.at(id));
  },
  move_from_to: function(from, to) {
    // we make the first few changes silently and only the last one triggers a re-draw
    var songs = this.get('songs');
    var song = songs.at(from);
    songs.remove(song, {silent: true});
    // if we move the current song, we need to update the position of the current song
    var current = this.get('current');
    if (from < current && to >= current) {
      this.set('current', current - 1, {silent: true});
    } else if (from > current && to <= current) {
      this.set('current', current + 1, {silent: true});
    } else if (from == current) {
      this.set('current', to, {silent: true});
    }
    songs.add(song, {at: to});
  }
});
