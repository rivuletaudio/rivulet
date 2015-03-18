var Playlist = Backbone.Model.extend({
  initialize: function() {
    var songs = this.get('songs');
    if (!(songs instanceof Backbone.Collection)) {
      this.set({
        songs: new SongCollection(this.get('songs'))
      });
    }
  },
  defaults: function() {
    return {
      title: 'Untitled',
      songs: new SongCollection()
    };
  },
  add_song: function(song) {
    var songs = this.get('songs');
    songs.add(song);
    App.save_playlists();
  },
  move_song_up: function(id) {
    if (id === 0) {
      return;
    }
    var songs = this.get('songs');
    songs.swap(id, id-1);
    App.save_playlists();
  },
  move_song_down: function(id) {
    var songs = this.get('songs');
    if (id === songs.length - 1) {
      return;
    }
    songs.swap(id, id+1);
    App.save_playlists();
  },
  remove_song: function(id) {
    var songs = this.get('songs');
    songs.remove(songs.at(id));
    App.save_playlists();
  }
});

var PlaylistCollection = Backbone.Collection.extend({
    model: Playlist
});
