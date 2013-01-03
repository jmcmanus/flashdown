from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.decks.models import Tag, Card
from libs.utils import get_login_forms
from libs.decorators import ajax_request


# Note: ensure_csrf_cookie required if template doesn't have forms
# containing the csrf_token tag. Forgetting about this has caused
# problems in the past so I'm leaving it here to prevent problems caused
# by future refactoring of templates.
@ensure_csrf_cookie
def overview(request):
    """Renders the main page."""
    decks = Tag.objects.filter(is_deck=True, deleted=False)
    ctx = {'decks': decks}
    ctx.update(get_login_forms(request))
    return render(request, 'decks/overview.html', ctx)

@ensure_csrf_cookie
def add_cards(request, deck_id=None):
    if deck_id is None:
        deck_id = request.COOKIES.get('active-deck-id', None)

    # TODO: what if we're passed some random string here using this cookie?

    decks = Tag.objects.filter(is_deck=True, deleted=False)

    if deck_id is None:
        if decks.count() > 0:
            deck_id = decks[0].pk
    else:
        try:
            Tag.objects.filter(pk=deck_id)
        except Tag.DoesNotExist:
            deck_id = None   # we got an invalid id

    if deck_id is not None:
        deck_id = int(deck_id)

    if decks == []:
        deck_id = None

    ctx = {'decks': decks, 'active_deck_id': deck_id}
    ctx.update(get_login_forms(request))
    return render(request, 'decks/addcards.html', ctx)

def review(request, deck_id):
    pass

def get_cards(request, deck_id):
    pass

def browse(request, deck_id=None):
    if deck_id is None:
        deck_id = request.COOKIES.get('active-deck-id', None)

    decks = Tag.objects.filter(is_deck=True, deleted=False)
    deck = None
    cards = None

    if deck_id is not None:
        try:
            deck = Tag.objects.get(pk=deck_id, deleted=False)
        except Tag.DoesNotExist:
            deck_id = None
    elif len(decks) > 0:
         # no deck_id, no active deck cookie - just get the first one
        deck_id = decks[0].pk
        deck = decks[0]

    if deck:
        if not deck.is_deck:  #TODO: do we care if we're browsing decks vs tags?
            deck = None
        else:
            cards = deck.deck_cards.filter(deleted=False)

    if deck_id is not None and deck_id != '':
        deck_id = int(deck_id)  # template will compre this to deck.id

    ctx = {'decks': decks, 'deck': deck,
           'cards': cards, 'active_deck_id': deck_id}
    ctx.update(get_login_forms(request))
    return render(request, 'decks/browse.html', ctx)

def cards(request, deck_id):
    deck = Tag.objects.get(pk=deck_id, deleted=False)
    if not deck.is_deck:  #TODO: do we care? change this method to view-tag?
        return HttpResponse(code=400)

    #cards = deck.deck_cards.all()
    cards = deck.deck_cards.filter(deleted=False)
    return render(request, 'decks/browse.html',
                  {'deck': deck, 'cards': cards})


###################################
# Primarily AJAX Functions        #
###################################

@ajax_request
def new_deck(request):
    """process an ajax request to add a new deck"""
    if not request.POST:  # we need the post data
        return HttpResponse()

    #TODO: validate data

    # currently the max deck name length is 50 characters
    deck_name = request.POST["deck_name"][:50]
    deck = None
    try:
        deck = Tag.objects.get(name=deck_name, deleted=False) # will be 0 or 1 of these
        return HttpResponse() # already exists, don't send a new list item
    except Tag.DoesNotExist:
        deck = Tag(name=deck_name, is_deck=True)
        deck.save()

    return render(request, 'decks/deckinfo_partial.html', {'deck' : deck})


@ajax_request
def delete_deck(request, deck_id):
    if not request.is_ajax() or request.method != 'POST':
        return HttpResponseBadRequest()

    deck = get_object_or_404(Tag, pk=deck_id, deleted=False)
    if not deck.is_deck:
        return HttpResponseBadRequest()

    deck.deleted = True # keep it around in case we want to restore it later
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

    if deck_id == '':
        return HttpResponseBadRequest('malformed deck id')

    deck_id = int(deck_id)
    deck = get_object_or_404(Tag, pk=deck_id)

    if not deck.is_deck:
        return HttpResponseBadRequest()

    front = request.POST["front"]
    back = request.POST["back"]

    card = Card(front=front, back=back, deck=deck)
    card.save()
    card.tags.add(deck)

    #todo: store additional tags

    return HttpResponse(status=201) # Created


@ajax_request
def get_card(request, card_id):
    try:
        card = Card.objects.get(pk=card_id, deleted=False)
    except Card.DoesNotExist:
        return HttpResponseNotFound

    return {'front': card.front, 'back': card.back}


@ajax_request
def delete_card(request, deck_id, card_id):
    if not request.is_ajax() or request.method != 'POST':
        return HttpResponseBadRequest()

    deck = get_object_or_404(Tag, pk=deck_id)
    if not deck.is_deck:
        return HttpResponseBadRequest()

    card = get_object_or_404(Card, pk=card_id)
    try:
        if not card.tags.filter(name=deck.name):
            return HttpResponseBadRequest()
    except:
        pass

    card.deleted = True # keep it around in case we want to restore it later
    card.save()

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

    try:
        card = Card.objects.get(pk=card_id, deleted=False)
        card.front = front
        card.back = back
        card.save()
    except Card.DoesNotExist:
        return HttpResponseNotFound()

    return HttpResponse()

# vim: set ai et ts=4 sw=4 sts=4 :

