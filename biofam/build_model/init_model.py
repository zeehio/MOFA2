
"""
Module to initialise a bioFAM model
"""

import scipy as s
import scipy.stats as stats
from sys import path
import sklearn.decomposition

from biofam.core.nodes import *

class initModel(object):
    def __init__(self, dim, data, lik):
        """
        PARAMETERS
        ----------
         dim: dictionary
            keyworded dimensionalities: N for the number of samples, M for the number of views, K for the number of latent variables, D for the number of features per view (a list)
         data: list of length M with ndarrays of dimensionality (N,Dm):
            observed data
         lik: list of length M with strings
            likelihood for each view
        """
        self.data = data
        self.lik = lik
        self.N = dim["N"]
        self.K = dim["K"]
        self.M = dim["M"]
        self.D = dim["D"]

        self.nodes = {}

    def initZ(self, pmean=0., pcov=1., qmean="random", qvar=1., qE=None, qE2=None, covariates=None,
              scale_covariates=None, precompute_pcovinv=True):
        """Method to initialise the latent variables
        PARAMETERS
        ----------
        pmean: mean of the prior distribution
        pcov: covariance of the prior distribution
        qmean: initial value of the mean of the variational distribution
        qvar: initial value of the variance of the variational distribution
        qE: initial value of the expectation of the variational distribution
        qE2: initial value of the second moment of the variational distribution
        covariates: covariates to be included as non-updated factors
            None if no covariates are present, or a ndarray covariates with dimensions (N,Kcovariates)
        scale_covariates: scale covariates to zero-mean and unit variance to match the prior?
            None if no covariates are present, or a ndarray with dimensions (Kcov,) indicating which covariates to scale
        precompute_pcovinv: precompute the inverse of the covariance matrice of the prior of Z
        """

        ## Initialise prior distribution (P) ##

        # mean
        pmean = s.ones((self.N, self.K)) * pmean

        # TODO add sanity check if not float (dim of the matrices)
        if isinstance(pcov, (int, float)):
            pcov = [s.sparse.eye(self.N) * pcov] * self.K

        ## Initialise variational distribution (Q) ##

        # variance
        qvar = s.ones((self.N, self.K)) * qvar

        # mean
        if qmean is not None:
            if isinstance(qmean, str):

                # Random initialisation
                if qmean == "random":
                    qmean = stats.norm.rvs(loc=0, scale=1, size=(self.N, self.K))

                # Random and orthogonal initialisation
                elif qmean == "orthogonal":
                    pca = sklearn.decomposition.PCA(n_components=self.K, copy=True, whiten=True)
                    pca.fit(stats.norm.rvs(loc=0, scale=1, size=(self.N, 9999)).T)
                    qmean = pca.components_.T

                # PCA initialisation
                elif qmean == "pca":
                    pca = sklearn.decomposition.PCA(n_components=self.K, copy=True, whiten=True)
                    pca.fit(s.concatenate(self.data, axis=0).T)
                    qmean = pca.components_.T

            elif isinstance(qmean, s.ndarray):
                assert qmean.shape == (self.N, self.K), "Wrong shape for the expectation of the Q distribution of Z"

            elif isinstance(qmean, (int, float)):
                qmean = s.ones((self.N, self.K)) * qmean

            else:
                print("Wrong initialisation for Z")
                exit()

        # Add covariates
        if covariates is not None:
            assert scale_covariates != None, "If you use covariates also define data_opts['scale_covariates']"

            # Select indices for covariates
            idx_covariates = s.array(range(covariates.shape[1]))

            # Center and scale the covariates to match the prior distribution N(0,1)
            scale_covariates = s.array(scale_covariates)
            covariates[:, scale_covariates] = (covariates[:, scale_covariates] - s.nanmean(
                covariates[:, scale_covariates], axis=0)) / s.nanstd(covariates[:, scale_covariates], axis=0)

            # Set to zero the missing values in the covariates
            covariates[s.isnan(covariates)] = 0.
            qmean[:, idx_covariates] = covariates

            # Remove prior and variational distributions from the covariates
            pcov[idx_covariates] = s.nan
            #pvar[:, idx_covariates] = s.nan
            qvar[:, idx_covariates] = s.nan  # MAYBE SET IT TO 0

        else:
            idx_covariates = None

        # Initialise the node
        self.nodes["Z"] = Z_Node(dim=(self.N, self.K), pmean=pmean, pcov=pcov, qmean=qmean, qvar=qvar, qE=qE, qE2=qE2,
                             idx_covariates=idx_covariates, precompute_pcovinv=precompute_pcovinv)

    def initSZ(self, pmean_T0=0., pmean_T1=0., pvar_T0=1., pvar_T1=1., ptheta=1., qmean_T0=0., qmean_T1=0., qvar_T0=1.,
              qvar_T1=1., qtheta=1., qEZ_T0=None, qEZ_T1=None, qET=None):
        """Method to initialise the factors (spike and slab reparametrised as the product of bernoulli and gaussian variables)
        PARAMETERS
        ----------
        (...)
        """
        # TODO : add different ways to initialise the parameters of the posterior of Z : random, random orthogonal , PCA
        # TODO : enable covariates (increasing K)

        ## Initialise prior distribution (P) ##

        ## Initialise variational distribution (Q) ##
        if isinstance(qmean_T1, str):

            if qmean_T1 == "random":  # random
                qmean_T1_tmp = stats.norm.rvs(loc=0, scale=1, size=(self.N, self.K))
            else:
                print("%s initialisation not implemented for Z" % qmean_T1)
                exit()

        elif isinstance(qmean_T1, s.ndarray):
            assert qmean_T1.shape == (self.N, self.K), "Wrong dimensionality"

        elif isinstance(qmean_T1, (int, float)):
            qmean_T1_tmp = s.ones((self.N, self.K)) * qmean_T1

        else:
            print("Wrong initialisation for Z")
            exit(1)

        self.nodes["SZ"] = SZ_Node(
            dim=(self.N, self.K),

            ptheta=ptheta,
            pmean_T0=pmean_T0,
            pvar_T0=pvar_T0,
            pmean_T1=pmean_T1,
            pvar_T1=pvar_T1,

            qtheta=qtheta,
            qmean_T0=qmean_T0,
            qvar_T0=qvar_T0,
            qmean_T1=qmean_T1_tmp,
            qvar_T1=qvar_T1,

            qET=qET,
            qEZ_T0=qEZ_T0,
            qEZ_T1=qEZ_T1,
        )

    def initW(self, pmean=0., pcov=1., qmean="random", qvar=1., qE=None, qE2=None, covariates=None,
              scale_covariates=None, precompute_pcovinv=None):
        """Method to initialise the weights
        PARAMETERS
        ----------
        pmean: mean of the prior distribution
        pvar: variance of the prior distribution
        qmean: initial value of the mean of the variational distribution
        qvar: initial value of the variance of the variational distribution
        qE: initial value of the expectation of the variational distribution
        qE2: initial value of the second moment of the variational distribution
        covariates: covariates to be included as non-updated weights
            None if no covariates are present, or a ndarray covariates with dimensions (N,Kcovariates)
        scale_covariates: scale covariates to zero-mean and unit variance to match the prior?
            None if no covariates are present, or a ndarray with dimensions (Kcov,) indicating which covariates to scale
        precompute_pcovinv: precompute the inverse of the covariance matrice of the prior of W
        """

        # Precompute the inverse of the covariance matrix of the gaussian prior of W
        if precompute_pcovinv is None:
            precompute_pcovinv = [True] * self.M

        # Add covariates
        if covariates is not None:
            assert scale_covariates != None, "If you use covariates also define data_opts['scale_covariates']"

            # Select indices for covariates
            idx_covariates = s.array(range(covariates.shape[1]))

            # Center and scale the covariates to match the prior distribution N(0,1)
            scale_covariates = s.array(scale_covariates)
            covariates[:, scale_covariates] = (covariates[:, scale_covariates] - s.nanmean(
                covariates[:, scale_covariates], axis=0)) / s.nanstd(covariates[:, scale_covariates], axis=0)

            # Set to zero the missing values in the covariates
            covariates[s.isnan(covariates)] = 0.
        else:
            idx_covariates = None

        W_list = [None] * self.M
        for m in range(self.M):

            ## Initialise prior distribution (P) ##

            # mean
            pmean_m = s.ones((self.D[m], self.K)) * pmean

            # covariance
            if isinstance(pcov, (int, float)):
                pcov_mk = s.sparse.eye(self.D[m]) * pcov
                pcov_m = [pcov_mk] * self.K

            ## Initialise variational distribution (Q) ##

            # variance
            qvar_m = s.ones((self.D[m], self.K)) * qvar

            # mean
            if qmean is not None:
                if isinstance(qmean, str):

                    # Random initialisation
                    if qmean == "random":
                        qmean_m = stats.norm.rvs(loc=0, scale=1, size=(self.D[m], self.K))

                    # Random and orthogonal initialisation
                    elif qmean == "orthogonal":
                        pca = sklearn.decomposition.PCA(n_components=self.K, copy=True, whiten=True)
                        pca.fit(stats.norm.rvs(loc=0, scale=1, size=(self.D[m], 9999)).T)
                        qmean_m = pca.components_.T

                    # PCA initialisation
                    elif qmean == "pca":
                        pca = sklearn.decomposition.PCA(n_components=self.K, copy=True, whiten=True)
                        pca.fit(s.concatenate(self.data, axis=0).T)
                        qmean_m = pca.components_.T

                elif isinstance(qmean, s.ndarray):
                    assert qmean.shape == (
                    self.D[m], self.K), "Wrong shape for the expectation of the Q distribution of W"
                    qmean_m = qmean

                elif isinstance(qmean, (int, float)):
                    qmean_m = s.ones((self.D[m], self.K)) * qmean

                else:
                    print("Wrong initialisation for W")
                    exit()

            else:
                qmean_m = None

            # Add covariates
            if covariates is not None:
                qmean_m[:, idx_covariates] = covariates

                # Remove prior and variational distributions from the covariates
                pcov_m[idx_covariates] = s.nan
                qvar_m[:, idx_covariates] = s.nan  # MAYBE SET IT TO 0

            # Initialise the node
            W_list[m] = W_Node(dim=(self.D[m], self.K), pmean=pmean_m, pcov=pcov_m, qmean=qmean_m, qvar=qvar_m, qE=qE, qE2=qE2,
                               idx_covariates=idx_covariates, precompute_pcovinv=precompute_pcovinv[m])

        self.nodes["W"] = Multiview_Variational_Node(self.M, *W_list)



    def initSW(self, pmean_S0=0., pmean_S1=0., pvar_S0=1., pvar_S1=1., ptheta=1., qmean_S0=0., qmean_S1=0., qvar_S0=1., qvar_S1=1., qtheta=1., qEW_S0=None, qEW_S1=None, qES=None):
        """Method to initialise the weights (spike and slab reparametrized as the product of bernoulli and gaussian variables)

        PARAMETERS
        ----------
        (...)
        """
        # TODO : add different ways to initialise the parameters of the posterior of W : random, random orthogonal , PCA
        # TODO : enable covariates (increasing K)

        W_list = [None]*self.M
        for m in range(self.M):

            ## Initialise prior distribution (P) ##

            ## Initialise variational distribution (Q) ##
            if isinstance(qmean_S1,str):

                if qmean_S1 == "random": # random
                    qmean_S1_tmp = stats.norm.rvs(loc=0, scale=1, size=(self.D[m],self.K))
                else:
                    print("%s initialisation not implemented for W" % qmean_S1)
                    exit()

            elif isinstance(qmean_S1,s.ndarray):
                assert qmean_S1.shape == (self.D[m],self.K), "Wrong dimensionality"

            elif isinstance(qmean_S1,(int,float)):
                qmean_S1_tmp = s.ones((self.D[m],self.K)) * qmean_S1

            else:
                print("Wrong initialisation for W")
                exit(1)

            W_list[m] = SW_Node(
                dim=(self.D[m],self.K),

                ptheta=ptheta,
                pmean_S0=pmean_S0,
                pvar_S0=pvar_S0,
                pmean_S1=pmean_S1,
                pvar_S1=pvar_S1,

                qtheta=qtheta,
                qmean_S0=qmean_S0,
                qvar_S0=qvar_S0,
                qmean_S1=qmean_S1_tmp,
                qvar_S1=qvar_S1,

                qES=qES,
                qEW_S0=qEW_S0,
                qEW_S1=qEW_S1,
            )

        self.nodes["SW"] = Multiview_Variational_Node(self.M, *W_list)

    def initAlphaZ_k(self, pa=1e-14, pb=1e-14, qa=1., qb=1., qE=None, qlnE=None):
        """Method to initialise the precision of the ARD prior on the factors

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: float
            initial expectation of the variational distribution
        """
        self.nodes["AlphaZ"] = AlphaZ_Node_k(dim=(self.K,), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE, qlnE=qlnE)

    def initAlphaZ_groups(self, groups, pa=1e-14, pb=1e-14, qa=1., qb=1., qE=None, qlnE=None):
        """Method to initialise the precision of the ARD prior per sample groups on the factors

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: float
            initial expectation of the variational distribution
        """
        # sanity checks
        assert len(groups) == self.N, 'sample groups labels do not match number of samples'

        # convert groups into integers from 0 to n_groups and keep the corresponding group names in groups_dic
        tmp = np.unique(groups, return_inverse=True)
        groups_dic = tmp[0]
        groups_ix = tmp[1]

        n_group = len(np.unique(groups_ix))
        assert len(groups_dic) == n_group, 'problem in np.unique'

        self.nodes["AlphaZ"] = AlphaZ_Node_groups(dim=(n_group, self.K), pa=pa, pb=pb, qa=qa, qb=qb, groups=groups_ix, groups_dic=groups_dic, qE=qE, qlnE=qlnE)

    def initSigmaZ_k(self, X, n_diag=0):
        '''Method to initialise the covariance prior structure on Z'''
        dim = (self.K,)
        self.Sigma = SigmaGrid_Node(dim, X, n_diag=n_diag)
        self.nodes["SigmaZ"] = self.Sigma

    def initSigmaBlockZ_k(self, X, clust, n_diag=0):
        '''Method to initialise the covariance prior structure on Z, for clusters assigned to samples'''
        dim = (self.K,)
        self.Sigma = BlockSigmaGrid_Node(dim, X, clust, n_diag=n_diag)
        self.nodes["SigmaZ"] = self.Sigma

    def initAlphaW_mk(self, pa=1e-14, pb=1e-14, qa=1., qb=1., qE=None, qlnE=None):
        """Method to initialise the precision of the ARD prior on the weights

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qa: float
            initialisation of the 'b' parameter of the variational distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: float
            initial expectation of the variational distribution
        """

        alpha_list = [None]*self.M
        for m in range(self.M):
            alpha_list[m] = AlphaW_Node_mk(dim=(self.K,), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE, qlnE=qlnE)
        self.nodes["AlphaW"] = Multiview_Variational_Node(self.M, *alpha_list)

    def initMixedSigmaAlphaW_mk(self,view_has_covariance_prior,params_views):
        '''Method to initialise the covariance prior structure or the Gamma variance on W for each view
        For each view, we choose between a covariance prior structure or a Gamma variance.

        PARAMETERS :
        -----------
        view_has_covariance_prior : list with for each view a boolean which takes value True if a covariance prior
        structure is choosen (or False if Gamma variance choosen)

        params_views : list with for each view the dict {pa ; pb ; qa ; qb; qE} of the Gamma variance
        or the dict {X, clust, n_diag} of the covariance prior structure
        '''

        AlphaSigmaNodes = [None] * self.M

        for m in range(self.M):

            params = params_views[m]
            dim = (self.K,)

            if view_has_covariance_prior[m]:
                # TODO add a if statement to check if there is a sigma_clust argument to see if blockSigma is needed
                if params['sigma_clust'] is None:
                    AlphaSigmaNodes[m]=SigmaGrid_Node(dim,params['X'], n_diag = params['n_diag'])
                else:
                    AlphaSigmaNodes[m]=SigmaBlockW_k(dim,params['X'], clust = params['sigma_clust'], n_diag = params['n_diag'])

            else:
                AlphaSigmaNodes[m] = AlphaW_Node_mk(dim,pa = params['pa'], pb = params['pb'], qa = params['qa'], qb = params['qb'])

        self.nodes["SigmaAlphaW"] = Multiview_Mixed_Node(self.M, *AlphaSigmaNodes)

    def initTau(self, pa=1e-14, pb=1e-14, qa=1., qb=1., qE=None, transposed=False):
        """Method to initialise the precision of the noise

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: float
            initial expectation of the variational distribution
        """

        tau_list = [None]*self.M
        for m in range(self.M):
            if self.lik[m] == "poisson":
                tmp = 0.25 + 0.17*s.amax(self.data[m],axis=0)
                tau_list[m] = Constant_Node(dim=(self.N, self.D[m]), value=tmp)
            elif self.lik[m] == "bernoulli":
                # tau_list[m] = Constant_Node(dim=(self.D[m],), value=s.ones(self.D[m])*0.25)
                # tau_list[m] = Tau_Jaakkola(dim=(self.D[m],), value=0.25)
                tau_list[m] = Tau_Jaakkola(dim=((self.N, self.D[m])), value=1.)
            elif self.lik[m] == "binomial":
                tmp = 0.25*s.amax(self.data["tot"][m],axis=0)
                tau_list[m] = Constant_Node(dim=(self.N, self.D[m]), value=tmp)
            elif self.lik[m] == "gaussian":
                if transposed:
                    tau_list[m] = TauN_Node(dim=(self.N,), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
                    print("Using TauN noise!")
                else:
                    tau_list[m] = TauD_Node(dim=(self.D[m],), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
            # elif self.lik[m] == "warp":
            #     tau_list[m] = Tau_Node(dim=(self.D[m],), pa=pa[m], pb=pb[m], qa=qa[m], qb=qb[m], qE=qE[m])
        self.nodes["Tau"] = Multiview_Mixed_Node(self.M, *tau_list)

    def initY(self, transpose_noise=False):
        """Method to initialise the observations"""
        Y_list = [None]*self.M
        for m in range(self.M):
            if self.lik[m]=="gaussian":
                Y_list[m] = Y_Node(dim=(self.N,self.D[m]), value=self.data[m], transpose_noise=transpose_noise)
            elif self.lik[m]=="poisson":
                # tmp = stats.norm.rvs(loc=0, scale=1, size=(self.N,self.D[m]))
                Y_list[m] = Poisson_PseudoY(dim=(self.N,self.D[m]), obs=self.data[m], E=None, transpose_noise=transpose_noise)
            elif self.lik[m]=="bernoulli":
                # Y_list[m] = Bernoulli_PseudoY(dim=(self.N,self.D[m]), obs=self.data[m], E=None)
                # tmp = stats.norm.rvs(loc=0, scale=1, size=(self.N,self.D[m]))
                Y_list[m] =  Bernoulli_PseudoY_Jaakkola(dim=(self.N,self.D[m]), obs=self.data[m], E=None, transpose_noise=transpose_noise)
                # Y_list[m] =  Bernoulli_PseudoY_Jaakkola(dim=(self.N,self.D[m]), obs=self.data[m], E=self.data[m])
            # elif self.lik[m]=="warp":
            #     print "Not implemented"
            #     exit()
            #     Y_list[m] = Warped_PseudoY_Node(dim=(self.N,self.D[m]), obs=self.data[m], func_type='tanh', I=3, E=None)
            #     Y_list[m] = Warped_PseudoY_Node(dim=(self.N,self.D[m]), obs=self.data[m], func_type='logistic', I=1, E=None)
        self.Y = Multiview_Mixed_Node(self.M, *Y_list)
        self.nodes["Y"] = self.Y

    def initThetaLearnZ_k(self, pa=1., pb=1., qa=1., qb=1., qE=None):
        """Method to initialise the sparsity parameter of the spike and slab factors

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: float
            initial expectation of the variational distribution
        """
        self.nodes["ThetaZ"] = ThetaZ_Node_k(dim=(self.K,), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)

    def initThetaMixedZ_k(self, idx, pa=1., pb=1., qa=1., qb=1., qE=None):
        """Method to initialise the sparsity parameter of the spike and slab factors
        In contrast with initThetaLearn, where a sparsity parameter is learnt by each feature and factor, and initThetaConst, where the sparsity is not learnt,
        in initThetaMixed the sparsity parameter is learnt by a subset of factors and features

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: (...)
        idx:list with binary matrices with dim (N,K)

        """

        # Do some sanity checks on the arguments
        if isinstance(qE, (int, float)):
            qE = s.ones((self.N, self.K)) * qE
        elif isinstance(qE, s.ndarray):
            assert qE.shape == (self.N, self.K), "Wrong dimensionality of Theta"

        # Initialise constant node
        Kconst = idx == 0
        if Kconst.sum() == 0:
            ConstThetaNode = None
        else:
            if qE is None:
                print("Wrong initialisation for Theta");
                exit()
            else:
                ConstThetaNode = ThetaZ_Constant_Node_k(dim=(self.N, s.sum(Kconst),), value=qE[:, Kconst], N_cells=1)
                self.nodes["ThetaZ"] = ConstThetaNode

        # Initialise non-constant node
        Klearn = idx == 1
        if Klearn.sum() == 0:
            LearnThetaNode = None
        else:
            # FOR NOW WE JUST TAKE THE FIRST ROW BECAUSE IT IS EXPANDED, THIS IS UGLY
            if qE is None:
                LearnThetaNode = ThetaZ_Node_k(dim=(s.sum(Klearn),), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
            else:
                LearnThetaNode = ThetaZ_Node_k(dim=(s.sum(Klearn),), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE[0, Klearn])
            self.nodes["ThetaZ"]=LearnThetaNode

        # Initialise mixed node
        if (ConstThetaNode is not None) and (LearnThetaNode is not None):
            self.nodes["ThetaZ"] = Mixed_ThetaZ_Nodes_k(LearnTheta=LearnThetaNode, ConstTheta=ConstThetaNode, idx=idx)


    def initThetaZConst_k(self, value=1.):
        """Method to initialise a constant sparsity parameter of the spike and slab factors

        PARAMETERS
        ----------
         value: ndarray
            constant value from 0 to 1 to initialise the node, 0 corresponds to complete sparsity (all weights are zero) and 1 corresponds to no sparsity
        """

        self.nodes["ThetaZ"] = ThetaZ_Constant_Node_k(dim=(self.N, self.K,), value=s.ones((self.N, self.K)) * value,
                                                      N_cells=1.)

    def initThetaLearnW_mk(self, pa=1., pb=1., qa=1., qb=1., qE=None):
        """Method to initialise the sparsity parameter of the spike and slab weights

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: float
            initial expectation of the variational distribution
        """
        Theta_list = [None] * self.M
        for m in range(self.M):
            Theta_list[m] = ThetaW_Node_mk(dim=(self.K,), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
        self.nodes["ThetaW"] = Multiview_Variational_Node(self.M, *Theta_list)

    def initThetaMixedW_mk(self, idx, pa=1., pb=1., qa=1., qb=1., qE=None):
        """Method to initialise the sparsity parameter of the spike and slab weights
        In contrast with initThetaLearn, where a sparsity parameter is learnt by each feature and factor, and initThetaConst, where the sparsity is not learnt,
        in initThetaMixed the sparsity parameter is learnt by a subset of factors and features

        PARAMETERS
        ----------
         pa: float
            'a' parameter of the prior distribution
         pb :float
            'b' parameter of the prior distribution
         qb: float
            initialisation of the 'b' parameter of the variational distribution
         qE: (...)
        idx:list with binary matrices with dim (D[m],K)

        """

        # Do some sanity checks on the arguments
        if isinstance(qE,list):
            assert len(qE) == self.M, "Wrong dimensionality"
            for m in range(self.M):
                if isinstance(qE[m],(int,float)):
                    qE[m] = s.ones((self.D[m],self.K)) * qE[m]
                elif isinstance(qE[m],s.ndarray):
                    assert qE[m].shape == (self.D[m],self.K), "Wrong dimensionality of Theta"
                else:
                    print("Wrong initialisation for Theta"); exit()

        elif isinstance(qE,s.ndarray):
            assert qE.shape == (self.D[m],self.K), "Wrong dimensionality of Theta"
            tmp = [ qE for m in range(self.M)]
            qE = tmp # IS THIS REQUIRED????


        elif isinstance(qE,(int,float)):
            tmp = [ s.ones((self.D[m],self.K)) * qE for m in range(self.M)]
            qE = tmp # IS THIS REQUIRED????

        Theta_list = [None] * self.M
        for m in range(self.M):

            # Initialise constant node
            Kconst = idx[m]==0
            if Kconst.sum() == 0:
                ConstThetaNode = None
            else:
                if qE is None:
                    print("Wrong initialisation for Theta");
                    exit()
                else:
                    ConstThetaNode = ThetaW_Constant_Node_mk(dim=(self.D[m],s.sum(Kconst),), value=qE[m][:,Kconst], N_cells=1)
                    Theta_list[m] = ConstThetaNode

            # Initialise non-constant node
            Klearn = idx[m]==1
            if Klearn.sum() == 0:
                LearnThetaNode = None
            else:
                if qE is None:
                    LearnThetaNode = ThetaW_Node_mk(dim=(s.sum(Klearn),), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE)
                else:
                    # FOR NOW WE JUST TAKE THE FIRST ROW BECAUSE IT IS EXPANDED, THIS IS UGLY
                    LearnThetaNode = ThetaW_Node_mk(dim=(s.sum(Klearn),), pa=pa, pb=pb, qa=qa, qb=qb, qE=qE[m][0,Klearn])
                Theta_list[m] = LearnThetaNode

            # Initialise mixed node
            if (ConstThetaNode is not None) and (LearnThetaNode is not None):
                Theta_list[m] = Mixed_ThetaW_Nodes_mk(LearnTheta=LearnThetaNode, ConstTheta=ConstThetaNode, idx=idx[m])

        self.Theta = Multiview_Mixed_Node(self.M, *Theta_list)
        self.nodes["ThetaW"] = self.Theta

    def initThetaConstW_mk(self, value=1.):
        """Method to initialise a constant sparsity parameter of the spike and slab weights

        PARAMETERS
        ----------
         value: ndarray
            constant value from 0 to 1 to initialise the node, 0 corresponds to complete sparsity (all weights are zero) and 1 corresponds to no sparsity
        """
        Theta_list = [None] * self.M
        for m in range(self.M):
            Theta_list[m] = ThetaW_Constant_Node_mk(dim=(self.D[m],self.K,), value=s.ones((self.D[m],self.K))*value, N_cells=1.)
        self.Theta = Multiview_Constant_Node(self.M, *Theta_list)
        self.nodes["ThetaW"] = self.Theta

    def initExpectations(self, *nodes):
        """ Method to initialise the expectations """
        for node in nodes:
            self.nodes[node].updateExpectations()

    def getNodes(self):
        """ Get method to return the nodes"""
        return self.nodes
        #return { k:v for (k,v) in self.nodes.items()}