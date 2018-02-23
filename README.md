#### 8:13 PM
Guido van Rossum is a cool guy. 
Do you think that’s because he has the same middle name as Jean-Claude Van Damme 
or do you think it’s because all Python core developers are cool?

For the record, he may have invented Python 3
but in 2014 he’s been doing all kinds of job for our friends at Dropbox.
He was using Python 2, just as everybody else there. False advertising.

#### 9:48 PM
The truth is Python 3 is great. 
I need to do something to help me take my mind off it.
Easy enough, except I need an idea.

I’m completely sober I’m not gonna lie.
So what if it’s 10PM and it’s a Friday night?
Github is open on my laptop and some of these Python repos have pretty horrendous (tabs for indentation) code.

My manager’s sitting here and had the idea of putting some of the worst Python repos
next to the best Perl repos and have people vote on which is better.

Good call, Mr. Manager.

#### 10:17 PM
Yea, it’s on. I’m not gonna do the Perl repos but I like the idea of comparing two repos together.
It gives the whole thing a very “Turing” feel since people’s ratings of the repos 
will be more implicit than, say, choosing a number to represent each repo's coolness 
like they do on ... nowhere.


The first thing we’re going to need is a lot of repos.

Fortunately, Github have everything I need, so I’ll just have to get all the repos from it.
Let the software engineering begin.

First up is calling Github API. They keep
everything open (with severe rate-limiting) so a little ```requests``` magic is all that’s necessary 
to download the top 1000 Python repos from Github.

Kids’ stuff.

#### 01:03 PM
No, actually first up is writing tests.

TDD. Moving right along.

PyCharm has just offered to update to 2017.3. Let's see what's new ...

#### 01:30 AM
Or maybe I should use Github's GraphQL API?

#### 01:45 AM
GraphQL is intense. Not only is there no
official Python library but there’s no library at all. Weird. That may be difficult, I'll come back later.

REST API is a little better. It’s
slightly obnoxious that nobody knows what REST is but there's Python library for it, so
it's definitely necessary to break out PyCharm and modify that Python script.

#### 02:08 AM (7 weeks later)
Done.

Perfect timing. Eduardo’s here and he’s
going to have the key ingredient: AWS_SECRET_ACCESS_KEY.
