from baseclass.SocialRecommender import SocialRecommender
from tool import config
from random import randint
from random import shuffle, choice
from collections import defaultdict
import numpy as np
from tool.qmath import sigmoid, cosine, cosine_sp
from math import log
from structure.symmetricMatrix import SymmetricMatrix
import os

from time import localtime, time, strftime
import matplotlib.pyplot as plt


class HER(SocialRecommender):
    def __init__(self, conf, trainingSet=None, testSet=None, relation=None, fold='[1]'):
        super(HER, self).__init__(conf, trainingSet, testSet, relation, fold)

    def readConfiguration(self):
        super(HER, self).readConfiguration()
        options = config.LineConfig(self.config['HER'])
        self.walkCount = int(options['-T'])
        self.walkLength = int(options['-L'])
        self.walkDim = int(options['-l'])
        self.winSize = int(options['-w'])
        self.topK = int(options['-k'])
        self.alpha = float(options['-a'])
        self.epoch = int(options['-ep'])
        self.neg = int(options['-neg'])
        self.rate = float(options['-r'])

    def printAlgorConfig(self):
        super(HER, self).printAlgorConfig()
        print 'Specified Arguments of', self.config['recommender'] + ':'
        print 'Walks count per user', self.walkCount
        print 'Length of each walk', self.walkLength
        print 'Dimension of user embedding', self.walkDim
        print '=' * 80

    def buildModel(self):
        self.b = np.random.random(self.dao.trainingSize()[1])
        #data clean
        cleanList = []
        cleanPair = []
        for user in self.sao.followees:
            if not self.dao.user.has_key(user):
                cleanList.append(user)
            for u2 in self.sao.followees[user]:
                if not self.dao.user.has_key(u2):
                    cleanPair.append((user, u2))
        for u in cleanList:
            del self.sao.followees[u]

        for pair in cleanPair:
            if self.sao.followees.has_key(pair[0]):
                del self.sao.followees[pair[0]][pair[1]]

        cleanList = []
        cleanPair = []
        for user in self.sao.followers:
            if not self.dao.user.has_key(user):
                cleanList.append(user)
            for u2 in self.sao.followers[user]:
                if not self.dao.user.has_key(u2):
                    cleanPair.append((user, u2))
        for u in cleanList:
            del self.sao.followers[u]

        for pair in cleanPair:
            if self.sao.followers.has_key(pair[0]):
                del self.sao.followers[pair[0]][pair[1]]

        # li = self.sao.followees.keys()
        #
        print 'Kind Note: This method will probably take much time.'
        # build U-F-NET
        print 'Building weighted user-friend network...'
        # filter isolated nodes and low ratings
        # Definition of Meta-Path
        p1 = 'UIU'
        p2 = 'UFU'
        p3 = 'UTU'
        p4 = 'UFIU'
        p5 = 'UFUIU'
        mPaths = [p1,p2,p3]#, p2, p3, p4,p5]

        self.G = np.random.rand(self.dao.trainingSize()[1], self.walkDim) / 10
        self.W = np.random.rand(self.dao.trainingSize()[0], self.walkDim) / 10

        self.fItems = {}  # filtered item set
        for item in self.dao.trainSet_i:
            self.fItems[item] = self.dao.trainSet_i[item].keys()

        self.fBuying = {}  # filtered buying set
        for user in self.dao.trainSet_u:
            self.fBuying[user] = []
            for item in self.dao.trainSet_u[user]:
                if self.fItems.has_key(item) and self.dao.trainSet_u[user][item] > 0.75:
                    self.fBuying[user].append(item)
            if self.fBuying[user] == []:
                del self.fBuying[user]


        self.UFNet = defaultdict(list)

        for user1 in self.sao.followees:
            s1 = set(self.sao.followees[user1])
            for user2 in self.sao.followees[user1]:
                if self.sao.followees.has_key(user2):
                    if user1 <> user2:
                        s2 = set(self.sao.followees[user2])
                        weight = len(s1.intersection(s2))
                        self.UFNet[user1] += [user2] * (weight + 1)

        self.UTNet = defaultdict(list)

        for user1 in self.sao.followers:
            s1 = set(self.sao.followers[user1])
            for user2 in self.sao.followers[user1]:
                if self.sao.followers.has_key(user2):
                    if user1 <> user2:
                        s2 = set(self.sao.followers[user2])
                        weight = len(s1.intersection(s2))
                        self.UTNet[user1] += [user2] * (weight + 1)
        #
        #
        #
        #
        print 'Generating random meta-path random walks...'
        self.walks = []
        #self.usercovered = {}


        for user in self.dao.user:

            for mp in mPaths:
                if mp == p1:
                    self.walkCount = 10
                if mp == p2:
                    self.walkCount = 10
                if mp == p3:
                    self.walkCount = 10
                if mp == p4:
                    self.walkCount = 10
                if mp == p5:
                    self.walkCount = 10
                for t in range(self.walkCount):

                    path = [(user, 'U')]
                    lastNode = user
                    nextNode = user
                    lastType = 'U'
                    for i in range(self.walkLength / len(mp)):

                        for tp in mp[1:]:
                            try:
                                if tp == 'I':

                                    nextNode = choice(self.fBuying[lastNode])

                                if tp == 'U':

                                    if lastType == 'I':
                                        nextNode = choice(self.fItems[lastNode])
                                    elif lastType == 'F':
                                        nextNode = choice(self.UFNet[lastNode])
                                        while not self.dao.user.has_key(nextNode):
                                            nextNode = choice(self.UFNet[lastNode])


                                if tp == 'F':

                                    nextNode = choice(self.UFNet[lastNode])
                                    while not self.dao.user.has_key(nextNode):
                                        nextNode = choice(self.UFNet[lastNode])

                                if tp == 'T':

                                    nextNode = choice(self.UTNet[lastNode])
                                    while not self.dao.user.has_key(nextNode):
                                        nextNode = choice(self.UTNet[lastNode])

                                path.append((nextNode, tp))
                                lastNode = nextNode
                                lastType = tp

                            except (KeyError, IndexError):
                                path = []
                                break

                    if path:
                        self.walks.append(path)
                        # for node in path:
                        #     if node[1] == 'U' or node[1] == 'F':
                        #         self.usercovered[node[0]] = 1
                                # print path
                                # if mp == 'UFIU':
                                # pass
        shuffle(self.walks)
        print 'walks:', len(self.walks)
        # Training get top-k friends
        print 'Generating user embedding...'
        # print 'user covered', len(self.usercovered)
        # print 'user coverage', float(len(self.usercovered)) / len(self.dao.user)
        # sampleWalks = []
        # sampleUser = {}
        # for i in range(1000):
        #     p = choice(self.walks)
        #     u = choice(p)
        #     while u[1]=='I':
        #         u = choice(p)
        #     if len(self.dao.trainSet_u[u[0]])<=10:
        #         sampleUser[u[0]] = 1
        #
        # print 'user coverage:', len(sampleUser)/float(1000)




        iteration = 1
        userList = self.dao.user.keys()
        itemList = self.dao.item.keys()
        self.topKSim = {}
        while iteration <= self.epoch:
            loss = 0

            for walk in self.walks:
                for i, node in enumerate(walk):
                    neighbors = walk[max(0, i - self.winSize / 2):min(len(walk) - 1, i + self.winSize / 2)]
                    center, ctp = walk[i]
                    if ctp == 'U' or ctp == 'F' or ctp == 'T':  # user
                        centerVec = self.W[self.dao.user[center]]
                    else:  # Item
                        centerVec = self.G[self.dao.item[center]]
                    for entity, tp in neighbors:
                        # negSamples = []
                        currentVec = ''
                        if tp == 'U' or tp == 'F' or tp=='T' and center <> entity:
                            currentVec = self.W[self.dao.user[entity]]
                            self.W[self.dao.user[entity]] +=   self.rate * (
                                1 - sigmoid(currentVec.dot(centerVec))) * centerVec
                            if ctp == 'U' or ctp == 'F' or ctp=='T':
                                self.W[self.dao.user[center]] +=   self.rate * (
                                    1 - sigmoid(currentVec.dot(centerVec))) * currentVec
                            else:
                                self.G[self.dao.item[center]] +=   self.rate * (
                                    1 - sigmoid(currentVec.dot(centerVec))) * currentVec
                            loss += -  log(sigmoid(currentVec.dot(centerVec)))
                            for i in range(self.neg):
                                sample = choice(userList)
                                while sample == entity:
                                    sample = choice(userList)
                                sampleVec = self.W[self.dao.user[sample]]
                                self.W[self.dao.user[sample]] -=   self.rate * (
                                    1 - sigmoid(-sampleVec.dot(centerVec))) * centerVec
                                if ctp == 'U' or ctp == 'F' or ctp == 'T':
                                    self.W[self.dao.user[center]] -=   self.rate * (
                                        1 - sigmoid(-sampleVec.dot(centerVec))) * sampleVec
                                else:
                                    self.G[self.dao.item[center]] -=   self.rate * (
                                        1 - sigmoid(-sampleVec.dot(centerVec))) * sampleVec
                                #loss += -  log(sigmoid(-sampleVec.dot(centerVec)))
                                # negSamples.append(choice)
                        elif tp == 'I' and center <> entity:
                            currentVec = self.G[self.dao.item[entity]]
                            self.G[self.dao.item[entity]] +=   self.rate * (
                                1 - sigmoid(currentVec.dot(centerVec))) * centerVec
                            if ctp == 'U' or ctp == 'F' or ctp == 'T':
                                self.W[self.dao.user[center]] +=   self.rate * (
                                    1 - sigmoid(currentVec.dot(centerVec))) * currentVec
                            else:
                                self.G[self.dao.item[center]] +=   self.rate * (
                                    1 - sigmoid(currentVec.dot(centerVec))) * currentVec
                            loss += -  log(sigmoid(currentVec.dot(centerVec)))
                            for i in range(self.neg):
                                sample = choice(itemList)
                                while sample == entity:
                                    sample = choice(itemList)
                                # negSamples.append(choice)
                                sampleVec = self.G[self.dao.item[sample]]
                                self.G[self.dao.item[sample]] -= self.rate * (
                                    1 - sigmoid(-currentVec.dot(centerVec))) * centerVec
                                if ctp == 'U' or ctp == 'F' or ctp == 'T':
                                    self.W[self.dao.user[center]] -=   self.rate * (
                                        1 - sigmoid(-sampleVec.dot(centerVec))) * sampleVec
                                else:
                                    self.G[self.dao.item[center]] -=   self.rate * (
                                        1 - sigmoid(-sampleVec.dot(centerVec))) * sampleVec
                                #loss += -self.alpha * log(sigmoid(-sampleVec.dot(centerVec)))
            shuffle(self.walks)

            print 'iteration:', iteration, 'loss:', loss
            iteration += 1

        print 'User embedding generated.'

        print 'Constructing similarity matrix...'
        i = 0


        for user1 in self.fBuying:
            uSim = []
            i+=1
            if i%200==0:
                print i,'/',len(self.fBuying)
            vec1 = self.W[self.dao.user[user1]]
            for user2 in self.fBuying:
                if user1 <> user2:
                    vec2 = self.W[self.dao.user[user2]]
                    sim = cosine(vec1, vec2)
                    uSim.append((user2,sim))

            self.topKSim[user1] = sorted(uSim, key=lambda d: d[1], reverse=True)[:self.topK]


        # print 'Similarity matrix finished.'
        # # # #print self.topKSim
        import pickle
        # # # #
        # # # #recordTime = strftime("%Y-%m-%d %H-%M-%S", localtime(time()))
        similarity = open('HER-lastfm-p3-sim'+self.foldInfo+'.pkl', 'wb')
        vectors = open('HER-lastfm-p3-vec'+self.foldInfo+'.pkl', 'wb')
        #Pickle dictionary using protocol 0.

        pickle.dump(self.topKSim, similarity)
        pickle.dump((self.W,self.G),vectors)
        similarity.close()
        vectors.close()

        # matrix decomposition
        #pkl_file = open('HER-lastfm-sim' + self.foldInfo + '.pkl', 'rb')

        #self.topKSim = pickle.load(pkl_file)

        print 'Decomposing...'
        self.F = np.random.rand(self.dao.trainingSize()[0], self.k) / 10
        # prepare Pu set, IPu set, and Nu set
        print 'Preparing item sets...'
        self.PositiveSet = defaultdict(dict)
        self.IPositiveSet = defaultdict(dict)


        for user in self.dao.user:
            for item in self.dao.trainSet_u[user]:
                if self.dao.trainSet_u[user][item] >= 1:
                    self.PositiveSet[user][item] = 1
                    # else:
                    #     self.NegativeSet[user].append(item)
            if self.topKSim.has_key(user):
                for friend in self.topKSim[user][:self.topK]:
                    if self.dao.user.has_key(friend):
                        for item in self.dao.trainSet_u[friend]:
                            if not self.PositiveSet[user].has_key(item):
                                if not self.IPositiveSet[user].has_key(item):
                                    self.IPositiveSet[user][item] = 1
                                else:
                                    self.IPositiveSet[user][item] += 1
        iteration = 0
        while iteration < self.maxIter:
            self.loss = 0
            itemList = self.dao.item.keys()

            for user in self.PositiveSet:
                kItems = self.IPositiveSet[user].keys()
                u = self.dao.user[user]
                for item in self.PositiveSet[user]:
                    i = self.dao.item[item]
                    if len(self.IPositiveSet[user]) > 0:
                        item_k = choice(kItems)
                        k = self.dao.item[item_k]
                        Suk = self.IPositiveSet[user][item_k]
                        self.P[u] += (1 / (Suk + 1)) * self.lRate * (1 - sigmoid(
                            (self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[k]) - self.b[k]) / (Suk + 1))) \
                                     * (self.Q[i] - self.Q[k])
                        self.Q[i] += (1 / (Suk + 1)) * self.lRate * (1 - sigmoid(
                            (self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[k]) - self.b[k]) / (
                                Suk + 1))) * \
                                     self.P[u]
                        self.Q[k] -= (1 / (Suk + 1)) * self.lRate * (1 - sigmoid(
                            (self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[k]) - self.b[k]) / (
                                Suk + 1))) * self.P[u]
                        self.b[i] += (1 / (Suk + 1)) * self.lRate * (1 - sigmoid(
                            (self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[k]) - self.b[k]) / (Suk + 1)))
                        self.b[k] -= (1 / (Suk + 1)) * self.lRate * (1 - sigmoid(
                            (self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[k]) - self.b[k]) / (Suk + 1)))
                        item_j = ''
                        # if len(self.NegativeSet[user])>0:
                        #     item_j = choice(self.NegativeSet[user])
                        # else:
                        item_j = choice(itemList)
                        while (self.PositiveSet[user].has_key(item_j) or self.IPositiveSet.has_key(item_j)):
                            item_j = choice(itemList)
                        j = self.dao.item[item_j]
                        self.P[u] += self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[k]) + self.b[k] - self.P[u].dot(self.Q[j]) - self.b[j])) * (
                                         self.Q[k] - self.Q[j])
                        self.Q[k] += self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[k]) + self.b[k] - self.P[u].dot(self.Q[j]) - self.b[j])) * \
                                     self.P[u]
                        self.Q[j] -= self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[k]) + self.b[k] - self.P[u].dot(self.Q[j]) - self.b[j])) * \
                                     self.P[u]
                        self.b[k] += self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[k]) + self.b[k] - self.P[u].dot(self.Q[j]) - self.b[j]))
                        self.b[j] -= self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[k]) + self.b[k] - self.P[u].dot(self.Q[j]) - self.b[j]))

                        self.P[u] -= self.lRate * self.regU * self.P[u]
                        self.Q[i] -= self.lRate * self.regI * self.Q[i]
                        self.Q[j] -= self.lRate * self.regI * self.Q[j]
                        self.Q[k] -= self.lRate * self.regI * self.Q[k]

                        self.loss += -log(sigmoid(
                            (self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[k]) - self.b[k]) / (Suk + 1))) \
                                     - log(
                            sigmoid(self.P[u].dot(self.Q[k]) + self.b[k] - self.P[u].dot(self.Q[j]) - self.b[j]))
                    else:
                        item_j = choice(itemList)
                        while (self.PositiveSet[user].has_key(item_j)):
                            item_j = choice(itemList)
                        j = self.dao.item[item_j]
                        self.P[u] += self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[j]) - self.b[j])) * (
                                         self.Q[i] - self.Q[j])
                        self.Q[i] += self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[j]) - self.b[j])) * \
                                     self.P[u]
                        self.Q[j] -= self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[j]) - self.b[j])) * \
                                     self.P[u]
                        self.b[i] += self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[j]) - self.b[j]))
                        self.b[j] -= self.lRate * (
                            1 - sigmoid(self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[j]) - self.b[j]))

                        self.loss += -log(
                            sigmoid(self.P[u].dot(self.Q[i]) + self.b[i] - self.P[u].dot(self.Q[j]) - self.b[j]))

                        self.loss += -log(sigmoid(self.P[u].dot(self.Q[i]) - self.P[u].dot(self.Q[j])))

            for user in self.topKSim:
                for friend in self.topKSim[user]:
                    u = self.dao.user[user]
                    f = self.dao.user[friend[0]]
                    self.P[u] -= self.alpha*self.lRate*(self.P[u]-self.P[f])

            self.loss += self.regU * (self.P * self.P).sum() + self.regI * (self.Q * self.Q).sum() + self.b.dot(self.b)
            iteration += 1
            if self.isConverged(iteration):
                break

    def predict(self,user,item):

        if self.dao.containsUser(user) and self.dao.containsItem(item):
            u = self.dao.getUserId(user)
            i = self.dao.getItemId(item)
            predictRating = sigmoid(self.Q[i].dot(self.P[u])+self.b[i])
            return predictRating
        else:
            return sigmoid(self.dao.globalMean)

    def predictForRanking(self, u):
        'invoked to rank all the items for the user'
        if self.dao.containsUser(u):
            u = self.dao.getUserId(u)
            return self.Q.dot(self.P[u])+self.b
        else:
            return [self.dao.globalMean] * len(self.dao.item)