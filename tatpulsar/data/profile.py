"""
The Class of Profile
"""
import numpy as np
import scipy.stats

__all__ = ['Profile',
        "phihist"]

class Profile():
    """
    Profile class

    Parameters
    ----------
    counts : array-like
        the counts in each phase bin of Profile

    cycles : int
        the period cycles of input Profile (default is 1).
        If cycles=2, the phase of profile would be ``np.linspace(0, 2, size_of_Profile+1)[:-1]``

    error : array-like
        the error of each phase bin, if not given the error will be the
        poisson error of counts (sqruare root of counts)

    Attributes
    ----------
    counts : array-like
        The counts in each phase bin of Profile
    phase : array-like
        The midpoints of phase bins
    phase_off : list
        The list of phase off interval, the two value are the left
        and right phase bin of off pulse phases.
        left_edge = phase_off[0]
        right_edge = phase_ff[1]
    ref_time : float, default None
        The reference time (in second) used to fold the profile
    """

    def __init__(self, counts, cycles=1, error=None):
        '''
        Parameters
        ----------
        counts : array-like
            the counts in each phase bin of Profile

        cycles : int
            the period cycles of input Profile (default is 1).
            If cycles=2, the phase of profile would be ``np.linspace(0, 2, size_of_Profile+1)[:-1]``

        error : array-like
            the error of each phase bin, if not given the error will be the
            poisson error of counts (sqruare root of counts)
        '''
        if type(cycles) != int:
            raise TypeError("The cycles of profile should be int")
        if cycles > 2:
            raise IOError("Why do you have to setup so many cycles? 2 cycles is enough.")
        if cycles == 2:
            self.counts = np.tile(counts, reps=2)
            self._pickled = True # whether the profile has been duplicated or modified
        else:
            self.counts = counts
            self._pickled = False # whether the profile has been duplicated or modified
        self.phase  = np.linspace(0, cycles, self.size+1)[:-1]
        if error is None:
            self.error = np.sqrt(self.counts)
        elif cycles == 2:
            self.error = np.tile(error, reps=2)
        else:
            self.error = error
        self._cycles = cycles
        self._pickled = False # whether the profile has been duplicated or modified
        self.ref_time = None

    def __add__(self, other):
        """
        merge two Profile.

        .. warning::

            When you add two Profile, we recommend that only add two Profile with ONE cycle.
            If you add two pickled Profile (e.g duplicated the phase into 2 cycles), the new
            returned Profile has a cycle of ONE, which is incorrect.

        """
        if not isinstance(other, Profile):
            raise IOError(f"{other} is not a Profile object")
        if self.cycles != other.cycles:
            raise ValueError("the cycles of two Profile object does not match")
        add_cnt = self.counts + other.counts
        add_err = np.sqrt(self.error**2 + other.error**2)
        return Profile(add_cnt, error=add_err)

    def __sub__(self, other):
        """
        subtract operator to subtract on Profile from another Profile
        """
        if not isinstance(other, Profile):
            raise IOError(f"{other} is not a Profile object")
        if self.cycles != other.cycles:
            raise ValueError("the cycles of two Profile object does not match")
        sub_cnt = self.counts - other.counts
        sub_err = np.sqrt(self.error**2 + other.error**2)
        return Profile(sub_cnt, error=sub_err)


    @property
    def cycles(self):
        return self._cycles
    @cycles.setter
    def cycles(self, value):
        """
        modify the cycles for profile
        """
        if value > 2:
            raise IOError("Why do you have to setup so many cycles? 2 cycles is enough.")

        if self._cycles == value:
            print(f"Cycle is already {value}, nothing to do")
        elif value == 2:
            self._cycles = value
            self.counts = np.tile(self.counts, reps=2)
            self.error  = np.tile(self.error, reps=2)
            self.phase  = np.linspace(0, value, self.size+1)[:-1]
        elif value == 1:
            self._cycles = value
            idx = int(self.counts.size/2)
            self.counts = self.counts[:idx]
            self.error  = self.error[:idx]
            self.phase  = np.linspace(0, value, self.size+1)[:-1]


    @property
    def size(self):
        if self.cycles = 2:
            return self.counts.size/2
        else:
            return self.counts.size

    @property
    def dof(self):
        """
        degree of freedom is :math:`(n-1)` where :math:`n` is the number of bins.
        """
        return self.size - 1

    @property
    def chisq(self):
        """
        chisquare statistic value of profile
        """
        if self.cycles = 2:
            idx = int(self.counts.size/2)
            counts = self.counts[:idx]
            error  = self.error[:idx]
        else:
            counts = self.counts
            error = self.error
        return np.sum( (counts - np.mean(counts))**2 / counts )

    @property
    def significance(self):
        """
        Return the significance in unit of sigma of given profile.
        """
        p_value = scipy.stats.chi2.sf(self.chisq, self.dof)
        # we are dealing with one-tailed tests
        sigma = scipy.stats.norm.isf(p_value)
        return sigma

    @property
    def pulsefrac(self):
        """
        Calculate the pulse fraction of given profile. The algorithm of
        calculating pulse fraction is:

        .. math::
            PF = (p_{\mathrm{max}} - p_{\mathrm{min}})/(p_{\mathrm{max}} + p_{\mathrm{min}})

        where :math:`p` is the counts of profile, please note the pulse fraction has valid physical
        meaning only if the input profile is folded by the net lightcurve or the background level can
        be well estimated and subtracted from the observed pulse profile.

        Returns
        -------
        pf: float
            The pulse fraction of profile
        pf_err: float
            The error of pulse fraction
        """
        pf = (self.counts.max() - self.counts.min()) / (self.counts.max() + self.counts.min())

        indx_max = np.argmax(self.counts)
        indx_min = np.argmin(self.counts)

        term1 = -2 * self.counts.max() / (self.counts.max() + self.counts.min())**2 * self.error[indx_min]
        term2 =  2 * self.counts.min() / (self.counts.max() + self.counts.min())**2 * self.error[indx_max]
        pf_err = np.sqrt(term1**2 + term2**2)
        return pf, pf_err

    def resample(self, sample_num=1, kind='poisson'):
        '''
        resampling the profile

        Parameters
        ----------
        sample_num : int, optional
            number of the resamplings for the profile, the default number is 1
        kind : str, optional
            The distribution of the profile, default is poisson.
            ('poisson', 'gaussian') are refering to the poisson and gauss distribution

        Returns
        -------
        resampled_profile : array or ndarray
            if sample_num == 1, return a one dimensional array
            if sample_num >1 , return a multi-dimensional array
        '''
        raw_profile = np.array(self.counts.tolist()*sample_num)
        if sample_num <= 0:
            raise IOError("The number of sampling must a positive integer")

        if kind == "poisson":
            resampled_profile = np.random.poisson(raw_profile)
        elif kind == "gaussian":
            pass #TODO

        resampled_profile = resampled_profile.reshape(int(resampled_profile.size/self.size),
                int(self.size))
        return resampled_profile

    def norm(self,
            method=0,
            bkg_range=None):
        '''
        normalize the profile, and return a normalized Profile object

        bkg_range is the background phase range selected to calculated the mean level
        of background, used in method=0.

        Parameters
        ----------
        method: int, optional
            The normalization method utilized, optional methods are {0, 1}
            method = 0 : :math:`N = (P - P_{min})/(P_{max} - P_{min})`
            if background range are selected (`bkg_range` is not None)
            :math:`N = (P - \\bar{B})/(P_{max} - \\bar{B})`
            where :math:`\\bar{B}` is the mean level in `bkg_range`
            method = 1 : :math:`N = (P-P_{min})/\\bar{P}`

        bkg_range: list, optional
            The background phase range for background estimation
        '''
        if method == 0:
            # without background section
            if bkg_range is None:
                norm_counts = (self.counts-np.min(self.counts))/\
                        (np.max(self.counts)-np.min(self.counts))

                X = self.counts
                m = self.counts.min()
                M = self.counts.max()
                delta_X = self.error
                delta_m = self.error[self.counts.argmin()]
                delta_M = self.error[self.counts.argmax()]
                delta_num = np.sqrt(delta_X**2 + delta_m**2)
                delta_den = np.sqrt(delta_M**2 + delta_m**2)

                expression = (X - m)/(M-m)
                norm_error = expression * np.sqrt((delta_num / (X - m))**2 + (delta_den / (M - m))**2)

            else:
                bkg_mask = (self.phase>=bkg_range[0]) & (self.phase<=bkg_range[1])
                bkg_counts = self.counts[bkg_mask]
                bkg_error  = self.error[bkg_mask]
                bkg_mean_error = np.sqrt(np.sum(bkg_error**2))/bkg_error.size
                norm_counts = (self.counts - np.mean(bkg_counts))/\
                        (np.max(self.counts) - np.mean(bkg_counts))

                X = self.counts
                m = np.mean(bkg_counts)
                M = self.counts.max()
                delta_X = self.error
                delta_m = bkg_mean_error
                delta_M = self.error[self.counts.argmax()]
                delta_num = np.sqrt(delta_X**2 + delta_m**2)
                delta_den = np.sqrt(delta_M**2 + delta_m**2)
                norm_error = np.sqrt(
                        self.error**2 + bkg_mean_error**2)/\
                                (np.max(self.counts) - np.mean(bkg_counts))
        elif method == 1:
            mean_error = np.sqrt(np.sum(self.error**2))/self.error.size
            norm_counts = (self.counts - np.min(self.counts))/\
                    np.mean(self.counts)

            X = self.counts
            m = self.counts.min()
            a = self.counts.mean()
            delta_X = self.error
            delta_m = self.error[self.counts.argmin()]
            delta_a = mean_error

            # calculate the uncertainty in (X - m)
            delta_Y = np.sqrt(delta_X**2 + delta_m**2)
            # calculate the expression and its uncertainty
            Y = X - m
            Z = Y / a
            norm_error = Z * np.sqrt((delta_Y / Y)**2 + (delta_a / a)**2)

        self.counts = norm_counts
        self.error  = norm_error

    def rebin(self, nbins):
        """
        rebin the profile into the given bin size
        """
        if nbins >= self.size

def phihist(phi, nbins, **kwargs):
    '''
    Ensure that the input and output of the histogram are appropriate.
    The input variables are the pulse phi of events, and the nbins.
    The counts of each bin are calculated by dividing [0, 1] into number of nbins.

    Parameters
    ----------
    phi : array
        a set of phase value of events.

    nbins : int
        the number of bins of profile

    Returns
    -------
    Profile : object
        return the object of Profile
    '''

    x = np.linspace(0, 1, nbins + 1)
    counts, phase = np.histogram(phi, x)
    profile_object = Profile(counts, **kwargs)

    return profile_object

# If the code works fine, don't easily modify/delete it
def resampling_profile(profile, sample_num=1, kind='poisson'):
     '''
     resampling the profile
     Parameters
     ----------
     profile : array
         The un-normalized profile
     sample_num : int, optional
         number of the resamplings for the profile, the default number is 1
     kind : str, optional
         The distribution of the profile, default is poisson.
         ('poisson', 'gaussian') are refering to the poisson and gauss distribution
     Returns
     -------
     resampled_profile : array or ndarray
         if sample_num == 1, return a one dimensional array
         if sample_num >1 , return a multi-dimensional array
     '''
     raw_profile = np.array(profile.tolist()*sample_num)
     if sample_num <= 0:
         raiseError("The number of sampling must a positive integer")

     if kind == "poisson":
         resampled_profile = np.random.poisson(raw_profile)
     elif kind == "gaussian":
         pass #TODO

     resampled_profile = resampled_profile.reshape(int(len(resampled_profile)/len(profile)),
             int(len(profile)))
     return resampled_profile
