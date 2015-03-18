var PlaylistView = Backbone.View.extend({
  template: Handlebars.compile($('#template-playlist').html()),
  song_template: Handlebars.compile($('#template-playlist-song').html()),

  events: {
    'click .add-current-playlist-play-link': 'add_play_playlist',
    'click .add-current-playlist-next-link': 'add_next_playlist',
    'click .add-current-playlist-last-link': 'add_last_playlist'
  },

  initialize: function() {
    this.songViews = [];
    this.render();
  },

  page_init: function(model) {
    if (!this.show) {
      if (this.model != model) {
        if (this.model) {
          this.stopListening(this.model);
        }
        this.model = model;
        this.listenTo(this.model.get('songs'), "change add remove reset swap", this.render);
        this.listenTo(this.model, "change reset add remove", this.render);
      }
      this.$el.html(this.template(this.model.toJSON()));
      this.show = true;
      this.render();
    }
  },

  page_off: function() {
    this.show = false;
    for (var i = 0; i < this.songViews.length; i++) {
      this.songViews[i].remove();
    }
    if (this.pqueue) {
      this.pqueue.cancel();
      delete this.pqueue;
    }
  },

  // TODO: write a function that lets me change the playlist being shown

  render: function() {
    if (!this.show) return;

    for (var i = 0; i < this.songViews.length; i++) {
      this.songViews[i].remove();
    }

    this.delegateEvents();
    var $ul = this.$el.find('ul.songs');
    $ul.empty();
    var playlistIndex = App.playlists.indexOf(this.model);
    var songs = this.model.get('songs');
    if (songs.length > 0) {
      var pos = 0;
      if (this.pqueue) {
        this.pqueue.cancel();
        delete this.pqueue;
      }
      this.pqueue = new ParallelQueue(3);
      songs.each(function(song) {
        var songView = new SongView({
          template: this.song_template,
          model: song,
          meta: {
            pos: pos,
            first: pos === 0,
            last: pos === songs.length - 1,
            playlist_idx: playlistIndex
          }
        });
        pos++;
        this.songViews.push(songView);
        $ul.append(songView.el);
        this.pqueue.add(songView.sources_search.bind(songView), [null]);
      }.bind(this));
    } else {
      $ul.append('<p>No songs in playlist.</p>');
    }

    // Same way to persist the playlist tab
    // TODO: find a better way...
    $('#tab-title-playlists').attr('href', '#playlist/' + playlistIndex);
  },

  add_play_playlist: function(e) {
    e.preventDefault();
    var songs = this.model.get('songs');
    App.play_queue.add_next((new SongCollection(songs.toJSON())).models);
    App.play_queue.play_next();
  },

  add_next_playlist: function(e) {
    e.preventDefault();
    var songs = this.model.get('songs');
    App.play_queue.add_next((new SongCollection(songs.toJSON())).models);
  },

  add_last_playlist: function(e) {
    e.preventDefault();
    var songs = this.model.get('songs');
    App.play_queue.add_last((new SongCollection(songs.toJSON())).models);
  }
});


var PlaylistsView = Backbone.View.extend({
  template: Handlebars.compile($('#template-playlists').html()),

  events: {
    'click .new-playlist-link': 'new_playlist',
    'click .remove-playlist': 'remove_playlist',
    'click .download-playlist': 'download_playlist',
    'click .upload-playlist': 'upload_playlist',
    'click .edit-link': 'edit_start',
    'click .no-edit-link': 'edit_stop',
    'click .add-playlist-play-link': 'add_play_playlist',
    'click .add-playlist-next-link': 'add_next_playlist',
    'click .add-playlist-last-link': 'add_last_playlist',
    'keypress input.edit-input': 'edit_keypress'
  },

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model, "change reset add remove", this.render);
    }
    this.render();
  },

  page_init: function() {
    if (!this.show) {
      this.$el.html(this.template());
      this.show = true;
      this.render();
    }
  },

  page_off: function() {
    this.show = false;
  },

  render: function() {
    if (!this.show) return;
    this.$el.html(this.template({playlists: this.model.toJSON()}));
    this.delegateEvents();
    App.save_playlists();
    
    // Same way to persist the playlist tab
    // TODO: find a better way...
    $('#tab-title-playlists').attr('href', '#playlists');
  },

  new_playlist: function(e) {
    e.preventDefault();
    this.model.add(new Playlist());
    this.$el.find('.playlist-entry:last').find('.title-no-edit').hide();
    this.$el.find('.playlist-entry:last').find('.title-edit').show();
    var $input = this.$el.find('.playlist-entry:last').find('input')[0];
    $input.focus();
    $input.setSelectionRange(0, $input.value.length);
  },

  remove_playlist: function(e) {
    e.preventDefault();
    var index = $(e.currentTarget).attr('data-index');
    this.model.remove(this.model.at(index));
  },

  upload_playlist: function(e) {
    function readSingleFile(e) {
      var file = e.target.files[0];
      if (!file) {
        return;
      }
      var reader = new FileReader();
      reader.onload = function(e) {
        var contents = e.target.result;
        displayContents(contents);
      };
      reader.readAsText(file);
    }
    var displayContents = function (contents) {
      this.model.add(JSON.parse(contents));
    }.bind(this);

    this.$el.find('.upload-hack').off('change');
    this.$el.find('.upload-hack').on('change', readSingleFile);
    this.$el.find('.upload-hack').click();

    e.preventDefault();
  },

  download_playlist: function(e) {
    e.preventDefault();
    function download(filename, text) {
      var pom = document.createElement('a');
      pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
      pom.setAttribute('download', filename);
      pom.click();
    }
    var index = $(e.currentTarget).attr('data-index');
    var playlist = this.model.at(index);
    var title = playlist.get('title');
    title = title.toLowerCase();
    title = title.replace(/\W/g, '_');
    download(title + '.wwp', JSON.stringify(playlist.toJSON()));
  },
  
  edit_start: function(e) {
    e.preventDefault();
    var $li = $(e.currentTarget).parent().parent().parent().parent().parent();
    $li.find('.title-no-edit').hide();
    $li.find('.title-edit').show();
    $li.find('input').focus();
  },

  edit_stop: function(e) {
    e.preventDefault();
    var $li = $(e.currentTarget).parent().parent().parent().parent().parent();
    var index = $li.find('input').attr('data-index');
    var title = $li.find('input').val();
    this.model.at(index).set('title', title);
    $li.find('.title-no-edit').show();
    $li.find('.title-edit').hide();
  },
  
  add_play_playlist: function(e) {
    e.preventDefault();
    var index = $(e.currentTarget).attr('data-index');
    var songs = this.model.at(index).get('songs');
    App.play_queue.add_next((new SongCollection(songs.toJSON())).models);
    App.play_queue.play_next();
  },
  
  add_next_playlist: function(e) {
    e.preventDefault();
    var index = $(e.currentTarget).attr('data-index');
    var songs = this.model.at(index).get('songs');
    App.play_queue.add_next((new SongCollection(songs.toJSON())).models);
  },
  
  add_last_playlist: function(e) {
    e.preventDefault();
    var index = $(e.currentTarget).attr('data-index');
    var songs = this.model.at(index).get('songs');
    App.play_queue.add_last((new SongCollection(songs.toJSON())).models);
  },

  edit_keypress: function(e) {
    if (e.which == 13) {
      e.preventDefault();
      var $li = $(e.currentTarget).parent().parent();
      var index = $li.find('input').attr('data-index');
      var title = $li.find('input').val();
      this.model.at(index).set('title', title, {silent: true});
      this.model.at(index).trigger('change');
      this.model.at(index).trigger('change:title');
      $li.find('.title-no-edit').show();
      $li.find('.title-edit').hide();
    }
  }  
});
