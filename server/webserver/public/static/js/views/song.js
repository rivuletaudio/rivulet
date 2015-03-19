var SongView = Backbone.View.extend({
  tagName: 'li',
  className: 'sortable',

  events: {
    'click .play-link':                  'play_song',
    'click .add-play-link':              'add_play_song',
    'click .sources-search':             'sources_search',
    'click .add-next-link':              'add_next_song',
    'click .add-last-link':              'add_last_song',
    'click .make-offline-link':          'make_offline',
    'click .download-link':              'download',
    'click .move-song-up-in-queue':      'move_song_up_in_queue',
    'click .move-song-down-in-queue':    'move_song_down_in_queue',
    'click .remove-song-in-queue':       'remove_song_in_queue',
    'click .add-to-playlist':            'add_to_playlist',
    'click .add-to-new-playlist':        'add_to_new_playlist',
    'click .move-song-up-in-playlist':   'move_song_up_in_playlist',
    'click .move-song-down-in-playlist': 'move_song_down_in_playlist',
    'click .remove-song-in-playlist':    'remove_song_in_playlist',
    'click .source-selector':            'select_source',
    'click .dropdown-hack-button':       'dropdown_hack'
  },

  initialize: function(params) {
    this.template = params.template;
    this.meta = params.meta;
    this.source_spinner_counter = 0;
    if (this.model) {
      this.listenTo(this.model.get_song_sources(), "add change reset", this.render);
      this.listenTo(this.model.get_song_sources().get('sources'), "add change reset", this.render);
      this.listenTo(this.model, "change", this.render);
    }
    this.statusInterval = setInterval(this.check_status.bind(this), 10000);
    this.check_status();
    this.render();
  },

  remove: function() {
    this.stopListening();
    this.undelegateEvents();
    clearInterval(this.statusInterval);
  },

  render: function() {
    var model = this.model.toJSON();

    var song_sources = this.model.get_song_sources();
    var sources  = song_sources.get('sources');
    var selected_id = song_sources.get('selected_id');
    model.sources = sources.length > 0 ? sources.toJSON() : undefined;
    model.selected_source_id = selected_id;
    model.meta = this.meta;

    // unique images for missing album art
    if (!model.image || !model.image.cover_url_small) {
      model.identicon = new Identicon(md5(model.artist + ' - ' + model.title), 34).toString();
    }

    // playlists to add to
    if (App.playlists.length > 0) {
      model.playlists = App.playlists.toJSON();
    }

    // compute the with of each piece of the progress bar
    model.pb_widths = model.pieces ? 100 / model.pieces.length : undefined;

    this.$el.html(this.template(model));
    this.delegateEvents();

    // as soon as we receive sources, check the status
    var had_sources = this.has_sources;
    this.has_sources = sources.length > 0;
    if (!had_sources && this.has_sources) {
      this.check_status();
    }

    if (this.source_spinner_counter > 0) {
      this.$el.find('.sources-spinner').show();
    }
  },

  check_status: function() {
    var source = this.model.get_song_sources().get_selected_source();
    if (source) {
      $.get('/status?info_hash=' + source.get('info_hash') + '&path=' + encodeURIComponent(source.get('path'))).success(function(data){
        var res = JSON.parse(data).result;
        var percent = Math.round(Number(res.progress) * 100, 2);
        var pieces = res.pieces;
        var requested = res.requested;
        // no change event is triggered if there is no change
        this.model.set({'percent-dl': percent, 'pieces': pieces, 'requested': requested});
      }.bind(this)).fail(function(){
        this.model.set({'percent-dl': undefined, 'pieces': undefined, 'requested': undefined});
      }.bind(this));
    }
  },

  play_song: function(e){
    e.preventDefault();
    App.play_queue.play_song(this.meta.pos);
  },

  add_play_song: function(e){
    e.preventDefault();
    var song = new Song(this.model.toJSON());
    App.play_queue.add_next(song);
    App.play_queue.play_next();
  },
  
  sources_search: function(e, cb){
    if (e) {
      e.preventDefault();
    }
    if (this.model.get_song_sources().get('sources').length) {
      if (cb) cb();
      return;
    }
    var $this = this.$el;
    var song = this.model;

    var tryShowSpinner = function() {
      if (this.source_spinner_counter === 0) {
        // spinner
        $this.find('.sources-spinner').show();
      }
      this.source_spinner_counter++;
    }.bind(this);
    
    var tryHideSpinner = function() {
      this.source_spinner_counter--;
      if (this.source_spinner_counter === 0) {
        $this.find('.sources-spinner').hide();
        if (cb) cb();
      }
    }.bind(this);
    
    // find more sources
    App.providers.each(function(provider) {
      if (provider.get('selected')) {
        tryShowSpinner();
        $.get('/sources',
              { artist: song.get('artist'),
                title: song.get('title'),
                provider_id: provider.get('index')
              }).success(function(data){
          var json = JSON.parse(data);
          var sources = json.result;
          song.add_sources(sources);
          tryHideSpinner();
        }).error(function(){
          console.log('error');
          tryHideSpinner();
        });
      }
    }, this);
  },

  add_next_song: function(e){
    e.preventDefault();
    // TODO: check if it's already downloading first
    this.model.download();
    var song = new Song(this.model.toJSON());
    App.play_queue.add_next(song);
  },

  add_last_song: function(e){
    e.preventDefault();
    // TODO: check if it's already downloading first
    this.model.download();
    var song = new Song(this.model.toJSON());
    App.play_queue.add_last(song);
  },

  make_offline: function(e){
    e.preventDefault();
    this.model.download();
  },

  download: function(e) {
    e.preventDefault();

    var download_song = function(play_link, filename) {
      console.log(play_link);
      var pom = document.createElement('a')
      pom.setAttribute('href', play_link)
      pom.setAttribute('download', filename)
      pom.click();
    };

    var title_to_filename = function(title) {
      var format = ".mp3";
      var title = title.split('.').join("");
      return title.toLowerCase() + format;
    };
    
    download_song(
      this.model.make_link('play'),
      title_to_filename(this.model.get('title')));
  },

  move_song_up_in_queue: function(e) {
    e.preventDefault();
    var id = this.meta.id;
    App.play_queue.move_song_up(this.meta.pos);
  },

  move_song_down_in_queue: function(e) {
    e.preventDefault();
    var id = this.meta.id;
    App.play_queue.move_song_down(this.meta.pos);
  },

  move_song_up_in_playlist: function(e) {
    e.preventDefault();
    App.playlists.at(this.meta.playlist_idx).move_song_up(this.meta.pos);
  },

  move_song_down_in_playlist: function(e) {
    e.preventDefault();
    App.playlists.at(this.meta.playlist_idx).move_song_down(this.meta.pos);
  },

  remove_song_in_queue: function(e) {
    e.preventDefault();
    App.play_queue.remove_song(this.meta.pos);
  },
  
  remove_song_in_playlist: function(e) {
    e.preventDefault();
    App.playlists.at(this.meta.playlist_idx).remove_song(this.meta.pos);
  },
  
  add_to_playlist: function(e) {
    e.preventDefault();
    var id = parseInt($(e.currentTarget).attr('playlist-id'));
    var song = new Song(this.model.toJSON());
    App.playlists.at(id).add_song(song);
  },

  add_to_new_playlist: function(e) {
    e.preventDefault();
    var title = prompt("Please enter a title for the new playlist", "Untitled");
    if (title != null) {
      var new_playlist = new Playlist();
      App.playlists.add(new_playlist);
      new_playlist.set('title', title);
      new_playlist.add_song(new Song(this.model.toJSON()));
    }
  },
  
  select_source: function(e) {
    e.preventDefault();
    var id = parseInt($(e.currentTarget).attr('data-index'));
    this.model.set_selected_id(id);
    this.check_status();
  },
  dropdown_hack: function(e) {
    var $button = $(e.currentTarget);
    var $dropdown = $button.parent().find('.dropdown-hack-menu');
    var dropDownTop = $button.offset().top;
    $dropdown.css('top', (dropDownTop - $dropdown.outerHeight()) + "px");
    $dropdown.css('left', $button.offset().left + "px");
  }
});
