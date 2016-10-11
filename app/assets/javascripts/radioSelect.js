(function(Modules) {

  "use strict";

  let states = {
    'initial': Hogan.compile(`
      <div class="radio-select-column">
        <label class="block-label js-block-label" for="{{name}}-0">
          <input checked="checked" id="{{name}}-0" name="{{name}}" type="radio" value=""> Now
        </label>
      </div>
      <div class="radio-select-column">
        {{#categories}}
          <input type='button' class='button tertiary-button js-category-button' value='{{.}}' />
        {{/categories}}
      </div>
    `),
    'choose': Hogan.compile(`
      <div class="radio-select-column">
        <label class="block-label js-block-label" for="{{name}}-0">
          <input checked="checked" id="{{name}}-0" name="{{name}}" type="radio" value="" class="js-initial-option"> Now
        </label>
      </div>
      <div class="radio-select-column">
        {{#choices}}
          <label class="block-label js-block-label" for="{{id}}">
            <input type="radio" value="{{value}}" id="{{id}}" name="{{name}}" class="js-option" />
            {{label}}
          </label>
        {{/choices}}
      </div>
    `),
    'chosen': Hogan.compile(`
      <div class="radio-select-column">
        <label class="block-label js-block-label" for="{{name}}-0">
          <input id="{{name}}-0" name="{{name}}" type="radio" value="" class="js-initial-option"> Now
        </label>
      </div>
      <div class="radio-select-column">
        {{#choices}}
          <label class="block-label js-block-label" for="{{id}}">
            <input checked="checked" type="radio" value="{{value}}" id="{{id}}" name="{{name}}" />
            {{label}}
          </label>
        {{/choices}}
      </div>
      <div class="radio-select-column">
        <input type='button' class='button tertiary-button js-reset-button' value='Choose a different time' />
      </div>
    `)
  };

  let focusSelected = function() {
    setTimeout(
      () => $('[type=radio]:checked').parent('label').blur().trigger('focus').addClass('selected'),
      10
    );
  };

  Modules.RadioSelect = function() {

    this.start = function(component) {

      let $component = $(component);
      let render = (state, data) => $component.html(states[state].render(data));
      let choices = $('label', $component).toArray().map(function(element) {
        let $element = $(element);
        return {
          'id': $element.attr('for'),
          'label': $.trim($element.text()),
          'value': $element.find('input').attr('value')
        };
      });
      let categories = $component.data('categories').split(',');
      let name = $component.find('input').eq(0).attr('name');

      $component
        .on('click', '.js-category-button', function(event) {

          event.preventDefault();
          let wordsInDay = $(this).attr('value').split(' ');
          let day = wordsInDay[wordsInDay.length - 1].toLowerCase();
          render('choose', {
            'choices': choices.filter(
              element => element.label.toLowerCase().indexOf(day) > -1
            ),
            'name': name
          });
          $('.js-option').eq(0).parent('label').trigger('focus');

        })
        .on('click', '.js-option', function(event) {

          // stop click being triggered by keyboard events
          if (!event.pageX) return true;

          event.preventDefault();
          let value = $(this).attr('value');
          render('chosen', {
            'choices': choices.filter(
              element => element.value == value
            ),
            'name': name
          });
          focusSelected();

        })
        .on('keydown', 'input[type=radio]', function(event) {

          // intercept keypresses which aren’t enter or space
          if (event.which !== 13 && event.which !== 32) {
            return true;
          }

          event.preventDefault();
          let value = $(this).attr('value');
          render('chosen', {
            'choices': choices.filter(
              element => element.value == value
            ),
            'name': name
          });
          focusSelected();

        })
        .on('click', '.js-reset-button', function(event) {

          event.preventDefault();
          render('initial', {
            'categories': categories,
            'name': name
          });
          focusSelected();

        });

      render('initial', {
        'categories': categories,
        'name': name
      });

      $component.css({'height': 'auto'});

    };

  };

})(window.GOVUK.Modules);
