(function(global) {

  "use strict";

  var Modules = global.GOVUK.Modules;
  var Hogan = global.Hogan;

  // Object holding all the states for the component's HTML
  let states = {
    'initial': Hogan.compile(`
      {{#showNowAsDefault}}
        <div class="radio-select__column">
          <div class="govuk-radios__item">
            <input class="govuk-radios__input" checked="checked" id="{{name}}-0" name="{{name}}" type="radio" value="">
            <label class="govuk-label govuk-radios__label" for="{{name}}-0">Now</label>
          </div>
        </div>
      {{/showNowAsDefault}}
      <div class="radio-select__column">
        {{#categories}}
          <input type='button' class='govuk-button govuk-button--secondary radio-select__button--category' aria-expanded="false" value='{{.}}' />
        {{/categories}}
      </div>
    `),
    'choose': Hogan.compile(`
      {{#showNowAsDefault}}
        <div class="radio-select__column">
          <div class="govuk-radios__item">
            <input class="govuk-radios__input" checked="checked" id="{{name}}-0" name="{{name}}" type="radio" value="">
            <label class="govuk-label govuk-radios__label" for="{{name}}-0">Now</label>
          </div>
        </div>
      {{/showNowAsDefault}}
      <div class="radio-select__column">
        {{#choices}}
          <div class="govuk-radios__item js-option">
            <input class="govuk-radios__input" type="radio" value="{{value}}" id="{{id}}" name="{{name}}" />
            <label class="govuk-label govuk-radios__label" for="{{id}}">{{label}}</label>
          </div>
        {{/choices}}
        <input type='button' class='govuk-button govuk-button--secondary radio-select__button--done' aria-expanded='true' value='Done' />
      </div>
    `),
    'chosen': Hogan.compile(`
      {{#showNowAsDefault}}
        <div class="radio-select__column">
          <div class="govuk-radios__item">
            <input class="govuk-radios__input" id="{{name}}-0" name="{{name}}" type="radio" value="">
            <label class="govuk-label govuk-radios__label" for="{{name}}-0">Now</label>
          </div>
        </div>
      {{/showNowAsDefault}}
      <div class="radio-select__column">
        {{#choices}}
          <div class="govuk-radios__item">
            <input class="govuk-radios__input" checked="checked" type="radio" value="{{value}}" id="{{id}}" name="{{name}}" />
            <label class="govuk-label govuk-radios__label" for="{{id}}">{{label}}</label>
          </div>
        {{/choices}}
      </div>
      <div class="radio-select__column">
        <input type='button' class='govuk-button govuk-button--secondary radio-select__button--reset' aria-expanded='false' value='Choose a different time' />
      </div>
    `)
  };

  let shiftFocus = function(elementToFocus, component) {
    // The first option is always the default
    if (elementToFocus === 'default') {
      $('[type=radio]', component).eq(0).focus();
    }
    if (elementToFocus === 'option') {
      $('[type=radio]', component).eq(1).focus();
    }
  };

  Modules.RadioSelect = function() {

    this.start = function(component) {

      let $component = $(component);
      let render = (state, data) => {
        $component.html(states[state].render(data));
      };
      // store array of all options in component
      let choices = $('label', $component).toArray().map(function(element) {
        let $element = $(element);
        return {
          'id': $element.attr('for'),
          'label': $.trim($element.text()),
          'value': $element.prev('input').attr('value')
        };
      });
      let categories = $component.data('categories').split(',');
      let name = $component.find('input').eq(0).attr('name');
      let mousedownOption = null;
      let showNowAsDefault = (
        $component.data('show-now-as-default').toString() === 'true' ?
        {'name': name} : false
      );

      // functions for changing the state of the component's HTML
      const reset = () => {
        render('initial', {
          'categories': categories,
          'name': name,
          'showNowAsDefault': showNowAsDefault
        });
        shiftFocus('default', component);
      };
      const selectOption = (value) => {
        render('chosen', {
          'choices': choices.filter(
            element => element.value == value
          ),
          'name': name,
          'showNowAsDefault': showNowAsDefault
        });
        shiftFocus('option', component);
      };

      // use mousedown + mouseup event sequence to confirm option selection
      const trackMouseup = (event) => {
        const parentNode = event.target.parentNode;

        if (parentNode === mousedownOption) {
          const value = $('input', parentNode).attr('value');

          selectOption(value);

          // clear tracking
          mousedownOption = null;
          $(document).off('mouseup', trackMouseup);
        }
      };

      // set events
      $component
        .on('click', '.radio-select__button--category', function(event) {

          event.preventDefault();
          let wordsInDay = $(this).attr('value').split(' ');
          let day = wordsInDay[wordsInDay.length - 1].toLowerCase();
          render('choose', {
            'choices': choices.filter(
              element => element.label.toLowerCase().indexOf(day) > -1
            ),
            'name': name,
            'showNowAsDefault': showNowAsDefault
          });
          shiftFocus('option', component);

        })
        .on('mousedown', '.js-option', function(event) {
          mousedownOption = this;

          // mouseup on the same option completes the click action
          $(document).on('mouseup', trackMouseup);
        })
        // space and enter, clicked on a radio confirm that option was selected
        .on('keydown', 'input[type=radio]', function(event) {

          // allow keypresses which aren’t enter or space through
          if (event.which !== 13 && event.which !== 32) {
            return true;
          }

          event.preventDefault();
          let value = $(this).attr('value');
          selectOption(value);

        })
        .on('click', '.radio-select__button--done', function(event) {

          event.preventDefault();
          let $selection = $('input[type=radio]:checked', this.parentNode);
          if ($selection.length) {

            render('chosen', {
              'choices': choices.filter(
                element => element.value == $selection.eq(0).attr('value')
              ),
              'name': name,
              'showNowAsDefault': showNowAsDefault
            });
            shiftFocus('option', component);

          } else {

            reset();
            shiftFocus('default', component);

          }

        })
        .on('click', '.radio-select__button--reset', function(event) {

          event.preventDefault();
          reset();
          shiftFocus('default', component);

        });

      // set HTML to initial state
      render('initial', {
        'categories': categories,
        'name': name,
        'showNowAsDefault': showNowAsDefault
      });

      $component.css({'height': 'auto'});

    };

  };

})(window);
