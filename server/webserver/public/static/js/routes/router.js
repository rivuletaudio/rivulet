var MainRouter = Backbone.Router.extend({

  routes: {
    "":                     "search",
    "search/:term":         "search",
    "search":               "search",
    "torrents":             "torrents",
    "playlists":            "playlists",
    "playlist/:idx":        "playlist",
    "providers":            "providers",
  },

  page_change: function(view, id, param) {
    $('.nav-buttons li').removeClass('active');
    $('#'+id).parent().addClass('active');
    for (var i in App.page_views) {
      if(App.page_views[i] != view) {
        App.page_views[i].page_off();
      }
    }
    view.page_init(param);
  },

  search: function(term) {
    this.page_change(App.search_results_view, 'tab-title-search');
    if (term) {
      $('#search-bar-input').val(term);
      App.search_results_view.search(term);
    }
  },

  playlists: function() {
    this.page_change(App.playlists_view, 'tab-title-playlists');
  },

  torrents: function() {
    App.torrents_view.reload();
    this.page_change(App.torrents_view, 'tab-title-torrents');
  },

  playlist: function(idx) {
    // This is duct tape. I can make this better later on...
    if (idx == -1) {
      // TODO: make a spinner
      var playlist = new Playlist({title: 'all available songs'});
      var songs = playlist.get('songs');
      $.get('/available_sources').success(function(data){
        var added = {};
        var available = JSON.parse(data).result;

        // search through your playlists and queue for songs that can be played right away
        // if a song is downloaded, but not in a playlist of any kind, we don't have metadata for it

        function handle_song (song){
          var source = song.get_song_sources().get_selected_source();
          if (!source) return;
          var info_hash = source.get('info_hash').toLowerCase();
          var path = source.get('path').toLowerCase();
          // not sure if necessary, but chop off the leading / if there is one
          if (path.length > 0 && path[0] == '/') {
            path = path.substr(1);
          }
          if(available[info_hash] && (available[info_hash][path] || available[info_hash][path_short])){
            // this shows each source only once
            // this is a shortcut; what we really want is to deduplicate the queue and the playlists
            if (!added[info_hash+path]) {
              songs.add(song);
              added[info_hash+path] = true;
            }
          }
        }

        App.playlists.each(function(playlist){
          playlist.get('songs').each(handle_song);
        });
        App.play_queue.get('songs').each(handle_song);

        this.page_change(App.playlist_view, 'tab-title-playlists', playlist);
      }.bind(this)).error(function() {
        this.page_change(App.playlist_view, 'tab-title-playlists', playlist);
      }.bind(this));
    } else {
      this.page_change(App.playlist_view, 'tab-title-playlists', App.playlists.at(idx));
    }
  },

  providers: function() {
    this.page_change(App.providers_view, 'tab-title-providers');
  }

});
