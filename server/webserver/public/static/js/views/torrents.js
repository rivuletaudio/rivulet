var TorrentsView = Backbone.View.extend({
  template: Handlebars.compile($('#template-torrents').html()),

  events: {
  },

  /**
   * http://codeaid.net/javascript/convert-size-in-bytes-to-human-readable-format-(javascript)
   * Convert number of bytes into human readable format
   *
   * @param integer bytes     Number of bytes to convert
   * @param integer precision Number of digits after the decimal separator
   * @return string
   */
  bytesToSize: function (bytes, precision) {  
      var kilobyte = 1024;
      var megabyte = kilobyte * 1024;
      var gigabyte = megabyte * 1024;
      var terabyte = gigabyte * 1024;
     
      if ((bytes >= 0) && (bytes < kilobyte)) {
          return bytes + ' B';
   
      } else if ((bytes >= kilobyte) && (bytes < megabyte)) {
          return (bytes / kilobyte).toFixed(precision) + ' KB';
   
      } else if ((bytes >= megabyte) && (bytes < gigabyte)) {
          return (bytes / megabyte).toFixed(precision) + ' MB';
   
      } else if ((bytes >= gigabyte) && (bytes < terabyte)) {
          return (bytes / gigabyte).toFixed(precision) + ' GB';
   
      } else if (bytes >= terabyte) {
          return (bytes / terabyte).toFixed(precision) + ' TB';
   
      } else {
          return bytes + ' B';
      }
  },

  initialize: function() {
    if (this.model) {
      this.listenTo(this.model, "change reset add remove", this.render);
    }
    this.render();
    this.filesViews = [];
  },

  page_init: function() {
    if (!this.show) {
      this.$el.html(this.template());
      this.show = true;
      this.render();
      this.timer = setInterval(this.reload.bind(this), 1000);
    }
  },

  page_off: function() {
    this.show = false;
    clearInterval(this.timer);
  },

  render: function() {
    if (!this.show) return;
    var model = this.model.toJSON();
    for (var i in model) {
      var torrent = model[i];
      torrent.download_rate = this.bytesToSize(torrent.download_rate, 2);
      torrent.upload_rate = this.bytesToSize(torrent.upload_rate, 2);
    }
    this.$el.html(this.template({torrents: model}));
    this.delegateEvents();
    App.save_playlists();

    // Same way to persist the playlist tab
    // TODO: find a better way...
    $('#tab-title-playlists').attr('href', '#playlists');
  },

  reload: function() {
    $.get('/torrents_status').success(function(data){
      this.model.reset(JSON.parse(data).result);
    }.bind(this)).error(function(){
      this.model.reset([]);
    }.bind(this));
  }
});
