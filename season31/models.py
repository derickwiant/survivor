import datetime

from django.db import models
from django.contrib.auth.models import User

class Castaway(models.Model):
	name = models.CharField(max_length = 32)
	full_name = models.CharField(max_length = 32)
	age = models.PositiveIntegerField(default = 0)
	occupation = models.CharField(max_length = 32)
	def __unicode__(self):
		return self.name
	def get_tribe(self):
		return self.castawayepisode_set.latest().tribe
	def get_first_initial(self):
		return self.name[0]
	def voted_out(self):
		voted_out = False
		for ce in self.castawayepisode_set.all():
			for action in ce.actions.all():
				if action == Action.objects.get(name = "Out"):
					return True
		return False
	class Meta:
		ordering = ('name',)

class Player(models.Model):
	user = models.OneToOneField(User)
	paid = models.BooleanField(default = False)
	hidden = models.BooleanField(default = False)
	def __unicode__(self):
		return self.user.username
	def get_full_name(self):
		return '%s %s' % (self.user.first_name, self.user.last_name)
	def get_latest_player_episode(self):
		return PlayerEpisode.objects.filter(player = self).latest()
	def get_latest_episode(self):
		return Episode.objects.latest()
	def get_leaderboard_players(self):
		return Player.objects.all()
	class Meta:
		ordering = ('user',)

class Tribe(models.Model):
	name = models.CharField(max_length = 32)
	color = models.CharField(max_length = 32)
	def __unicode__(self):
		return self.name
	def get_all_episodes(self):
		return get_all_episodes()
	class Meta:
		ordering = ('name',)

class Action(models.Model):
	name = models.CharField(max_length = 32)
	score = models.IntegerField(default = 1)
	icon_filename = models.CharField(max_length = 32)
	def __unicode__(self):
		return self.name
	class Meta:
		ordering = ('name',)
		
class Episode(models.Model):
	title = models.CharField(max_length = 64)
	number = models.PositiveIntegerField(default = 0)
	air_date = models.DateTimeField()
	players = models.ManyToManyField(Player, through = 'PlayerEpisode', through_fields = ('episode', 'player'))
	castaways = models.ManyToManyField(Castaway, through = 'CastawayEpisode', through_fields = ('episode', 'castaway'))
	team_size = models.PositiveIntegerField(default = 5)
	def __unicode__(self):
		return "Episode %i" % (self.number)
	def update_scores(self):
		return update_scores()
	def get_prev_episode(self):
		try:
			prev_e = Episode.objects.get(number = self.number - 1)
		except:
			prev_e = None
		return prev_e
	def get_next_episode(self):
		try:
			next_e = Episode.objects.get(number = self.number + 1)
		except:
			next_e = None
		return next_e
	def short(self):
		return "E%s" % ("{0:02d}".format(self.number))
	def air_day(self):
		return self.air_date.strftime("%A")
	class Meta:
		ordering = ('number',)
		get_latest_by = 'air_date'

class PlayerEpisode(models.Model):
	player = models.ForeignKey(Player)
	episode = models.ForeignKey(Episode)
	correctly_predicted_votes = models.PositiveIntegerField(default = 0)
	action_score = models.IntegerField(default = 0)
	vote_off_score = models.PositiveIntegerField(default = 0)
	jsp_score = models.PositiveIntegerField(default = 0)
	week_score = models.IntegerField(default = 0)
	total_score = models.IntegerField(default = 0)
	movement = models.IntegerField(default = 0)
	place = models.PositiveIntegerField(default = 0)
	has_score_changed = models.BooleanField(default = False)
	def __unicode__(self):
		return "%s | %s" % (self.player.user.username, self.episode)
	def get_team_picks(self):
		return self.pick_set.filter(type = 'TM').all()
	def get_vote_picks(self):
		return self.pick_set.filter(type = 'VO').all()
	def clear_team_picks(self):
		for pick in self.get_team_picks():
			pick.delete()
	def clear_vote_picks(self):
		for pick in self.get_vote_picks():
			pick.delete()
	def get_pick_options(self):
		return CastawayEpisode.objects.filter(episode = Episode.objects.latest()).all()
	def get_loyalty_bonus(self):
		loyalty_bonus = 0;
		if self.episode.number == 1:
			return 0
		last_ue = PlayerEpisode.objects.get(player = self.player, episode = Episode.objects.get(number = self.episode.number - 1))
		if not last_ue:
			return 0
		for pick in self.get_team_picks():
			for last_pick in last_ue.get_team_picks():
				if pick.castaway_episode.castaway == last_pick.castaway_episode.castaway:
					loyalty_bonus += 1;
		return loyalty_bonus
	def update_score(self):
		self.week_score = 0
		self.total_score = 0
		self.action_score = 0
		self.jsp_score = 0
		self.correctly_predicted_votes = 0
		teampicks = self.get_team_picks()
		votepicks = self.get_vote_picks()
		for pick in teampicks:
			ce = pick.castaway_episode
			self.action_score += ce.score
		for pick in votepicks:	
			try:
				vo_action = pick.castaway_episode.actions.filter(name = "Out") # TODO: dont hardcode this name
			except:
				vo_action = None
			if vo_action:
				self.correctly_predicted_votes += 1;
		self.vote_off_score = self.correctly_predicted_votes * 10 # TODO: dont hardcode this score
		self.week_score = self.action_score + self.vote_off_score + self.jsp_score + self.get_loyalty_bonus()
	class Meta:
		ordering = ('episode', 'player')
		get_latest_by = 'episode'

class CastawayEpisode(models.Model):
	castaway = models.ForeignKey(Castaway)
	episode = models.ForeignKey(Episode)
	tribe = models.ForeignKey(Tribe)
	actions = models.ManyToManyField(Action, blank = True)
	score = models.IntegerField(default = 0)
	has_score_changed = models.BooleanField(default = False)
	def __unicode__(self):
		return "%s | %s" % (self.castaway.name, self.episode)
	def update_score(self):
		self.score = 0
		for action in self.actions.all():
			self.score += action.score
	class Meta:
		ordering = ('episode', 'tribe', 'castaway')
		get_latest_by = 'episode'

class Pick(models.Model):
	player_episode = models.ForeignKey(PlayerEpisode)
	castaway_episode = models.ForeignKey(CastawayEpisode)
	TYPES = (
		('TM', 'Team Member'),
		('VO', 'Vote Off')
	)
	type = models.CharField(max_length = 2, choices = TYPES, default = "TM")
	def __unicode__(self):
		return "%s | %s picked %s for %s" % (self.player_episode.episode, self.player_episode.player.user.username, self.castaway_episode.castaway.name, self.type)
	class Meta:
		ordering = ('castaway_episode', 'type', 'player_episode')

class Vote(models.Model):
	castaway_episode = models.ForeignKey(CastawayEpisode)
	castaway = models.ForeignKey(Castaway)
	is_ftc_vote = models.BooleanField(default = False)
	def __unicode__(self):
		return "%s | %s voted for %s" % (self.castaway_episode.episode, self.castaway_episode.castaway.name, self.castaway.name)
	class Meta:
		ordering = ('castaway_episode', 'castaway')
