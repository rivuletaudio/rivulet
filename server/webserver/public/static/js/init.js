function supports_html5_storage() {
  try {
    return 'localStorage' in window && window['localStorage'] !== null;
  } catch (e) {
    return false;
  }
}

$(function(){
  var app_el = $('#app')[0];

  var avaliable_providers = [{
    title: "Kickass",
    index: 0,
    selected: true
  }, {
    title: "OldPirateBay",
    index: 1,
    selected: true
  }, {
    title: "ThePirateBay",
    index: 2,
    selected: true
  }];
  
  window.App = {};
  App.load_song_sources = function() {
    if (supports_html5_storage()) {
      var song_sources = localStorage['song_sources'];
      if (song_sources) {
        song_sources = JSON.parse(song_sources);
        for (var key in song_sources) {
          song_sources[key] = new SongSources(song_sources[key]);
        }
      } else {
        song_sources = {};
      }
      App.song_sources = song_sources;
    }
  };
  App.save_song_sources = function() {
    if (supports_html5_storage()) {
      var song_sources = {};
      for (var key in App.song_sources) {
        song_sources[key] = App.song_sources[key].toJSON();
      }
      localStorage['song_sources'] = JSON.stringify(song_sources);
    }
  };
  App.load_playlists = function() {
    if (supports_html5_storage()) {
      var playlists = localStorage['playlists'];
      if (playlists) {
        playlists = JSON.parse(playlists);
        playlists = new PlaylistCollection(playlists);
      } else {
        playlists = new PlaylistCollection();
      }
      App.playlists = playlists;
    }
  };
  App.save_playlists = function() {
    if (supports_html5_storage()) {
      localStorage['playlists'] = JSON.stringify(App.playlists.toJSON());
    }
  };
  App.load_providers = function() {
    if (supports_html5_storage()) {
      var providers = localStorage['providers'];
      if (providers) {
        providers = JSON.parse(providers);
        providers = new ProviderCollection(providers);

        var new_providers = avaliable_providers.filter(function(avaliable_provider) {
          return !(providers.some(function(provider) {
            return provider.get('title') === avaliable_provider.title;
          }, this));
        }, this);

        var old_providers = providers.filter(function(provider) {
          return !(avaliable_providers.some(function(avaliable_provider) {
            return provider.get('title') === avaliable_provider.title;
          }, this));
        }, this);

        providers.add(new_providers);
        providers.remove(old_providers);
        
      } else {
        providers = new ProviderCollection(avaliable_providers);
      }
      App.providers = providers;
    }
  };
  App.save_providers = function() {
    if (supports_html5_storage()) {
      localStorage['providers'] = JSON.stringify(App.providers.toJSON());
    }
  };
  App.load_song_sources();
  App.load_playlists();
  App.load_providers();
  App.play_queue = new PlayQueue();
  App.search_results_model = new SearchResults();
  App.torrents = new TorrentCollection();
 
  App.player_view = new PlayerView({
    el: $('#player')[0],
    model: App.play_queue
  });

  App.queue_view = new QueueView({
    el: $('#queue')[0],
    model: App.play_queue
  });

  App.search_results_view = new SearchResultsView({
    el: app_el,
    model: App.search_results_model
  });

  App.playlists_view = new PlaylistsView({
    el: app_el,
    model: App.playlists
  });

  App.torrents_view = new TorrentsView({
    el: app_el,
    model: App.torrents
  });

  App.playlist_view = new PlaylistView({
    el: app_el
  });

  App.providers_view = new ProvidersView({
    el: app_el,
    model: App.providers
  });
 
  App.page_views = [App.search_results_view,
                    App.playlist_view,
                    App.playlists_view,
                    App.torrents_view,
                    App.providers_view];

  var bar_cb = function(e){
    e.preventDefault();
    App.main_router.navigate('search/' +
      encodeURIComponent($('#search-bar-input').val()),
      {trigger: true});
  };

  $('#search-bar-form').submit(bar_cb);

  App.main_router = new MainRouter();

  Backbone.history.start()
});
