var Song = Backbone.Model.extend({
  defaults: function() {
    return {
      title: 'Untitled',
      artist: 'Anonymous'
    };
  },

  hash: function() {
    return this.get('artist') + ' - ' + this.get('title');
  },

  get_song_sources: function() {
    var song_sources = window.App.song_sources[this.hash()] || new SongSources();
    window.App.song_sources[this.hash()] = song_sources;
    return song_sources;
  },
  
  set_selected_id: function(id) {
    this.get_song_sources().set('selected_id', id);
    App.save_song_sources();
  },  
 
  add_source: function(new_source) {
    var song_sources = window.App.song_sources[this.hash()] || new SongSources();
    var sources = song_sources.get('sources');
    
    var dup_sources = sources.filter(function(source) {
      return source.get('info_hash') == new_source.info_hash &&
        source.get('path') == new_source.path;
    }, this);

    if (dup_sources.length === 0) {
      song_sources.add_source(new_source);
    } else {
      var dup_source = dup_sources[0];
      
      if (!dup_source.get('magnet') && new_source.magnet) {
        dup_source.set('magnet', new_source.magnet);
      }

      if (!dup_source.get('torrent_link') && new_source.torrent_link) {
        dup_source.set('torrent_link', new_source.torrent_link);
      }
    }


    window.App.song_sources[this.hash()] = song_sources;
    window.App.save_song_sources();
  },
  
  add_sources: function(new_sources) {
    if (!new_sources) return;
    for (var i = 0; i < new_sources.length; i++) {
      this.add_source(new_sources[i]);
    }
  },

  make_link: function(url){
    var source = this.get_song_sources().get_selected_source();
    if (source) {
      source = source.toJSON();
      if (source.torrent_link) {
        return url + '?' + this.encode_params('torrent_link', source.torrent_link, source.path);
      } else if (source.magnet) {
        return url + '?' + this.encode_params('magnet', source.magnet, source.path);
      } else {
        return url + '?' + this.encode_params('info_hash', source.info_hash, source.path);
      }
    } else {
      return undefined;
    }
  },

  // type is one of torrent_link, magnet, info_hash
  encode_params: function(type, src, path) {
    return type+'='+encodeURIComponent(src)+'&path='+encodeURIComponent(path)
  },

  download: function() {
    $.get(this.make_link('download')).success(function() {
      this.set('downloading', true);
    }.bind(this)).error(function(){
      this.set('downloading', false);
    }.bind(this));
  }

});

var SongCollection = Backbone.Collection.extend({
  model: Song,
  swap: function(index1, index2) {
    this.models[index1] = this.models.splice(index2, 1, this.models[index1])[0];
    this.trigger('swap', this.models);
  }
});
