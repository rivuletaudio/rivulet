var ProvidersView = Backbone.View.extend({
  template: Handlebars.compile($('#template-providers').html()),

  events: {
    'click .provider-selector': 'update_provider'
  },
  
  initialize: function() {
    if (this.model) {
      this.listenTo(this.model, "change", this.render);
    }
    this.render()
  },

  page_init: function() {
    if (!this.show) {
      this.show = true;
      this.render();
    }
  },

  page_off: function() {
    this.show = false;
  },

  render: function() {
    if (!this.show) return;
    this.$el.html(this.template({
      providers: this.model.toJSON()
    }));
  },

  update_provider: function(e) {
    e.preventDefault();
    var index = $(e.currentTarget).attr('data-index');
    var provider = this.model.at(index);
    provider.set('selected', !provider.get('selected'));
    App.save_providers();
  }
});
