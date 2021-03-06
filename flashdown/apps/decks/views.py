from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext, loader

from apps.decks.models import Deck, Card
from apps.decks.forms import DeckForm

from libs.decorators import ajax_request, login_required

import functools
login_required = functools.partial(login_required, login_url='index')


#TODO: add splash page and make this login_required as well
@login_required
def overview(request):
    """Renders the main dashboard page."""
    decks = Deck.objects.filter(active=True, owner=request.user)
    ctx = {'decks': decks, 'deck_form': DeckForm()}

    if not request.POST:
        return render(request, 'decks/overview.html', ctx)

@login_required
def add_cards(request, deck_id=None):
    """Card editing page. User can add new cards to their decks."""
    (deck_id, __, decks) = resolve_deck_id(request, deck_id)

    request.session['active_deck_id'] = deck_id

    ctx = {'decks': decks, 'active_deck_id': deck_id}
    return render(request, 'decks/addcards.html', ctx)


@login_required
def browse(request, deck_id=None):
    """Browse decks and their associated cards."""
    (deck_id, deck, decks) = resolve_deck_id(request, deck_id)
    cards = deck.deck_cards.filter(active=True) if deck else None

    request.session['active_deck_id'] = deck_id

    ctx = {'decks': decks, 'deck': deck,
           'cards': cards, 'active_deck_id': deck_id}

    return render(request, 'decks/browse.html', ctx)


@login_required
def review(request, deck_id):
    """Review/study a given deck."""
    deck = get_object_or_404(Deck, pk=deck_id, owner=request.user, active=True)
    cards = deck.deck_cards.filter(active=True)
    #TODO: if len(cards) == 0, in review.html show message that there's nothing to review

    request.session['active_deck_id'] = deck_id

    return render(request, 'decks/review.html', {'deck': deck, 'cards': cards})


###################################
# Primarily AJAX Functions        #
###################################

#TODO: unused
@ajax_request
def get_cards(request, deck_id):
    """Get a json list of cards for a given deck."""
    deck = Deck.objects.get_object_or_404(pk=deck_id, owner=request.user,
                                          active=True)
    cards = deck.deck_cards.filter(active=True).values();
    deck = deck.values()
    return {'deck': deck, 'cards': cards}


@ajax_request
def delete_deck(request, deck_id):
    if not request.user.is_authenticated():
        return HttpResponse(status=401)

    if not request.is_ajax() or request.method != 'POST':
        return HttpResponseBadRequest()

    deck = get_object_or_404(Deck, pk=deck_id, owner=request.user, active=True)
    deck.active = False # keep it around in case we want to restore it later
    deck.save()

    return HttpResponse() #status=200 OK


@ajax_request
def new_card(request):
    if request.method != 'POST':
        return HttpResponseBadRequest()

    deck_id = request.POST.get("deck-id")
    front = request.POST.get("front")
    back = request.POST.get("back")

    if not all([deck_id, front, back]): # Not None, not ''
        return HttpResponseBadRequest('missing data')

    deck = get_object_or_404(Deck, pk=int(deck_id), owner=request.user)

    card = Card(front=front, back=back, deck=deck, owner=request.user)
    card.save()

    request.session['active_deck_id'] = deck_id

    return HttpResponse(status=201) # Created


@ajax_request
def new_deck(request):
    if request.method != 'POST':
        return HttpResponseBadRequest()

    t = loader.get_template('decks/new_deck_modal.html')
    form = DeckForm(request.POST)
    if not form.is_valid():
        c = RequestContext(request, {'deck_form': form, 'form_only': True})
        form_html = t.render(c)
        return {'form_html': form_html, 'success': False}

    deck = form.save(commit=False)
    deck.owner = request.user
    deck.save()

    request.session['active_deck_id'] = deck.pk

    c = RequestContext(request, {'deck_form': DeckForm(), 'form_only': True})
    form_html = t.render(c)

    t2 = loader.get_template('decks/deckinfo_partial.html')
    c2 = RequestContext(request, {'deck': deck})
    deck_html = t2.render(c2)

    return {'form_html': form_html, 'deck_html': deck_html, 'success': True}


@ajax_request
def get_card(request, card_id):
    card = get_object_or_404(Card, pk=card_id, owner=request.user, active=True)
    return {'front': card.front, 'back': card.back}


@ajax_request
def delete_card(request, deck_id, card_id):
    if not request.is_ajax() or request.method != 'POST':
        return HttpResponseBadRequest()

    deck = get_object_or_404(Deck, pk=deck_id, owner=request.user, active=True)
    card = get_object_or_404(Card, pk=card_id, owner=request.user, active=True, deck=deck)
    card.active = False # keep it around in case we want to restore it later
    card.save()

    request.session['active_deck_id'] = deck_id

    return HttpResponse()


@ajax_request
def update_card(request):
    if request.method != 'POST':
        return HttpResponseBadRequest()

    card_id = request.POST.get('card_id')
    front = request.POST.get('front')
    back = request.POST.get('back')

    if not all([card_id, front, back]): # not None, not empty
        return HttpResponseBadRequest()

    card = get_object_or_404(Card, pk=card_id, owner=request.user, active=True)
    card.front = front
    card.back = back
    card.save()

    return HttpResponse()


## Utility Methods ##

def resolve_deck_id(request, deck_id):
    """
    Returned deck_id is first of these that is valid:
    [stored active deck id, id of first deck], else None.
    Returns deck_id and the list of decks.
    """
    if deck_id is None:
        deck_id = request.session.get('active_deck_id', None)

    decks = Deck.objects.filter(active=True, owner=request.user)
    deck = None

    # first try, using the given deck id
    if deck_id:
        try:
            deck = Deck.objects.get(pk=deck_id, active=True, owner=request.user)
        except Deck.DoesNotExist:
            deck_id = None   # we got an invalid id

    # next try, using the first active deck
    if not deck_id and len(decks) > 0:
        deck = decks[0]
        deck_id = deck.pk

    deck_id = int(deck_id) if deck_id else None

    return (deck_id, deck, decks)


# vim: set ai et ts=4 sw=4 sts=4 :
