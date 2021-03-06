# StaticGeneratorMem for Django

## Introduction

StaticGeneratorMem is based on StaticGenerator, a python class for django that generates static files out of your dynamic app which you can serve with apache or nginx to decrease load on your server. StaticGeneratorMem does pretty much the same but instead of storing the content as static files it puts it in memcached so you can serve it directly with nginx and its memcached module.

Serving static files with nginx is faster, but it serves fast from nginx aswell. Use either staticgenerator or staticgeneratormem for your blog or content heavy site to decrease server load.

## Usage

StaticGeneratorMem is a drop-in replacement for StaticGenerator. If you're already using StaticGenerator the only thing you need to do with your django settings is to configure the cache backend to use memcached. You also need to update your nginx config to read from memcached.

Add something like this to your settings.py if you alread haven't.
    
    CACHE_BACKEND = 'memcached://127.0.0.1:11211/'

If you have'nt used StaticGenerator before, read on.

### Method 1 (preferred): Middleware

A middleware is available to generate the file only when the URL is requested. This solves the 404 Problem (see below).

First, add Regexes of URLs you want to cache to `settings.py` like so:

    STATIC_GENERATOR_URLS = (
        r'^/$',
        r'^/blog',
        r'^/about',
    )
    
Second, add the Middleware to `MIDDLEWARE_CLASSES`:

    MIDDLEWARE_CLASSES = (
        ...snip...
        'staticgenerator.middleware.StaticGeneratorMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        ...snip...
    )
    
**Note**: You must place the StaticGeneratorMiddleware before FlatpageFallbackMiddleware if you use it.
    
When the pages are accessed for the first time, the body of the page is saved into a memcached. This is completely transparent to the end-user. When the page or an associated object has changed, simply delete the cached file (See notes on Signals).

### Method 2: Generate on Save

The second method works by saving the cache file on save. This method fakes a request to get the appropriate content. In this example we want to publish our home page, all live Posts and all FlatPages:

    # Passing url, a QuerySet and Model
    from staticgeneratormem import quick_publish
    quick_publish('/', Post.objects.live(), FlatPage)

Deleting paths is just as easy:

    from staticgeneratormem import quick_delete
    quick_delete('/path-to-delete/')


#### The "404 Problem"

(This text about the "404 Problem" is from the StaticGenerator README. It's not really a problem if you something like "if self.is_published: quick_publish...  in your save method")

The second method suffers from a problem herein called the "404 problem". Say you have a blog post that is not yet to be published. When you save it, the file created is actually a 404 message since the blog post is not actually available to the public. Using the older method you'd have to re-save the object to generate the file again.

The new method solves this because it saves the file only when the URL is accessed successfully (read: only when the HTTP status is 200).

### Using Signals

Integrating with existing models is easy using [Django’s signal dispatcher](http://code.djangoproject.com/wiki/Signals). Simply create a function to delete your models, and connect to the dispatcher:

    from django.contrib.flatpages.models import FlatPage
    from blog.models import Post
    from staticgeneratormem import quick_delete
    from django.db.models.signals import post_save, post_delete

    def update_page_signal(sender, **kwargs):
        quick_delete('/','/sitemap.xml',kwargs['instance'])
        try:
            if not settings.DEBUG:
                ping_google(sitemap_url='/sitemap.xml')
        except Exception:
            pass

    post_save.connect(update_page_signal, sender=Post)
    post_delete.connect(update_page_signal, sender=Post)
    post_save.connect(update_page_signal, sender=FlatPage)
    post_delete.connect(update_page_signal, sender=FlatPage)
    
Every time you save a Post or FlatPage it deletes the file from memcached. Delete the ping google and sitemap.xml stuff if you are not using it (you should). What happens when a comment is added? Just delete the corresponding page:

    from django.contrib.comments.models import Comment

    def publish_comment(sender, **kwargs):
        quick_delete(kwargs['instance'].get_content_object())

    post_save.connect(publish_comment, sender=Comment)
    post_delete.connect(publish_comment, sender=Comment)
    
## Configure your front-end

### Sample Nginx configuration

This configuration snippet shows how Nginx can automatically serve content from memcached generated by StaticGeneratorMem, and pass all Django requests to Apache or whatever httpd you are using to serve django. 

    # This example configuration only shows relevant parts
    # It assumes your django app is served via http on localhost:9004
    location / {
        #pass POST requests to django
        if ($request_method = POST) {
                proxy_pass http://localhost:9004;
                break;
        }
        default_type  "text/html; charset=utf-8";
        set $memcached_key "$host$uri";
        memcached_pass localhost:11211;
        error_page 404 502 = /django;
    }
    
    location = /django  {
        proxy_pass http://localhost:9004;
        break;
    }
    
Note! As you see the $host var is used in the $memcached_key variable. This value will probably be the same as you set your server_name to, example.com for example. You need to set the variable SERVER_NAME in your settings.py to the same value OR if you are using contrib.sites, set the domain field for your current site id to example.com (preferred).

### Serve from cache only for non logged in users

StaticGeneratorMem includes a feature not included in StaticGenerator.
You can set the variable 
    
    STATIC_GENERATOR_ANON_ONLY = True

in your settings.py which will cause the included middleware to only save to memcached on non-logged-in requests. Then add the following lines so your nginx config looks something like this.

    # This example configuration only shows relevant parts
    # It assumes your django app is served via http on localhost:9004
    location / {
        #pass POST requests to django
        if ($request_method = POST) {
                proxy_pass http://localhost:9004;
                break;
        }
        if ($http_cookie ~* "sessionid=.{32}") {
            proxy_pass http://localhost:9004;
            break;
        }
        default_type  "text/html; charset=utf-8";
        set $memcached_key "$host$uri";
        memcached_pass localhost:11211;
        error_page 404 502 = /django;
    }
    
    location = /django  {
        proxy_pass http://localhost:9004;
        break;
    }

If you use another name for your session id cookie than sessionid you need to change that in the above example. It's not 100% perfect, it seems like upon logout the sessionid cookie stays, causing loggedin-then-logged-out users not to hit the cache. Not a big deal on blogs and content sites, should only be you and any other authors. 
    
## It’s not for Everything

The beauty of the generator is that you choose when and what urls are made into cache. Obviously a contact form or search form won’t work this way, so we just leave them as regular Django requests. In your front-end http server (you are using a front-end web server, right?) just set the URLs you want to be served as static and they’re already being served.

## Feedback

Love it? Hate it? [Let me know what you think!](http://twitter.com/andriijas)