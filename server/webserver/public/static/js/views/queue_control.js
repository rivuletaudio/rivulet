var QueueControlView = Backbone.View.extend({
  
  template: Handlebars.compile($('#template-queue-control').html()),

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model, "change", this.render);
      this.listenTo(this.model.get('songs'), "change add remove reset", this.render);
      this.listenTo(App.playlists, "change add remove", this.render);
      this.listenTo(this.model, 'next_song_request', this.fetch_next_song);
    }
    this.render();
  },

  render: function() {
    var model = this.model.toJSON();
    model.playlists = App.playlists.toJSON();
    this.$el.empty().html(this.template(model));
    return this;
  },

  events: {
    "click .add-queue-to-new-playlist": "add_to_new_playlist",
    "click .add-queue-to-playlist":     "add_to_playlist",
    "click .dropdown-hack-button":      "dropdown_hack",
    "click .toggle-radio-button":       "radio_toggle"
  },

  radio_toggle: function(e){
    e.preventDefault();
    var $this = $(e.currentTarget);
    $this.blur();
    this.model.set('radio', !this.model.get('radio'));
    if (!this.model.get('radio')) {
      this.model.set('radio-song', null);
    } else {
      this.fetch_next_song();
    }
  },

  fetch_next_song: function(){
    this.model.set('radio-song', null);
    var songs = this.model.get('songs');
    if (songs.length > 0) {
console.log('get');
      var last_song = songs.at(songs.length-1);
      $.get('/similar?artist=' +
          encodeURIComponent(last_song.get('artist')) +
          '&title=' +
          encodeURIComponent(last_song.get('title'))
          ).success(function(data){
console.log('success');
        var json = JSON.parse(data);
        var song;
        if (json.result.length > 0) {
console.log('results');
          queue_json = songs.toJSON();
          // try to pick a song we don't already have in the queue
          chosen_song = null;
          console.log('result length', json.result.length);
          // this logic can be much simpler. Sorry. I'm tired.
          for (var i in json.result) {
            var song_json = json.result[i];
            var artist = song_json.artist;
            var title = song_json.title;
            console.log('queue json length', queue_json.length);
            chosen_song = song_json;
            for (var j in queue_json) {
              var queue_song = queue_json[j];
              console.log('test');
              console.log(queue_song, song_json);
              console.log(queue_song.artist == artist && queue_song.title == title);
              if (queue_song.artist == artist && queue_song.title == title) {
                // we already have this song in the queue; skip it
                chosen_song = null;
                break;
              }
            }
            if (chosen_song) {
              break;
            }
          }
          if (chosen_song) {
            song = new Song(chosen_song);
          } else {
            // TODO: fix code duplication
            song = new Song({artist: "Johnny Cash", title: "I Walk the Line", image: {cover_url_medium: 'http://userserve-ak.last.fm/serve/64s/103653991.png'}});
          }
        } else {
console.log('no results');
          // randomly chosen song by a fair die
          song = new Song({artist: "Johnny Cash", title: "I Walk the Line", image: {cover_url_medium: 'http://userserve-ak.last.fm/serve/64s/103653991.png'}});
        }
        var sources = song.get_song_sources();
        this.model.set('radio-song', song);
        if (sources.get('sources').length) {
console.log('has source');
          this.radio_got_sources();
        } else {
console.log('has no source');
          song.sources_search_common(this.radio_got_sources.bind(this), true);
        }
      }.bind(this)).error(function(){
console.log('error');
        this.model.set('radio', false);
      }.bind(this));
    } else {
      // TODO make it work when you have no songs in queue
      this.model.set('radio', false);
    }
  },

  //TODO: don't assume success!
  radio_got_sources: function() {
    console.log('got sources');
    this.model.trigger('change');
  },

  add_to_playlist: function(e) {
    e.preventDefault();
    var id = parseInt($(e.currentTarget).attr('playlist-id'));
    App.playlists.at(id).add_song(this.model.get('songs').toJSON());
  },
  
  add_to_new_playlist: function(e) {
    e.preventDefault();
    
    var title = prompt("Please enter a title for the new playlist", "Untitled");
    if (title != null) {
      var new_playlist = new Playlist();
      App.playlists.add(new_playlist);
      new_playlist.set('title', title);
      new_playlist.add_song(this.model.get('songs').toJSON());
    }
  },

  dropdown_hack: function(e) {
    var $button = $(e.currentTarget);
    var $dropdown = $button.parent().find('.dropdown-hack-menu');
    var dropDownTop = $button.offset().top;
    $dropdown.css('top', (dropDownTop - $dropdown.outerHeight()) + "px");
  }

});
  
