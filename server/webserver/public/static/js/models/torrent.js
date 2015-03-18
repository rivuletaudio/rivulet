var Torrent = Backbone.Model.extend({
  defaults: function() {
    return {
      name: 'Unknown Torrent'
    };
  }
});

var TorrentCollection = Backbone.Collection.extend({
  model: Torrent
});
