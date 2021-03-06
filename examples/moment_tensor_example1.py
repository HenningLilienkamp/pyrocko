from pyrocko import moment_tensor as mtm

magnitude = 6.3  # Magnitude of the earthquake

exp = mtm.magnitude_to_moment(magnitude)  # convert the mag to moment in [Nm]

m = mtm.MomentTensor()  # init pyrocko moment tensor
m.mnn = 2.34*exp
m.mee = -2.64*exp
m.mdd = 0.295*exp
m.mne = 1.49*exp
m.mnd = 0.182*exp
m.med = -0.975*exp

print(m)  # print moment tensor

# gives out both nodal planes:
(s1, d1, r1), (s2, d2, r2) = m.both_strike_dip_rake()

print('strike1=%s, dip1=%s, rake1=%s' % (s1, d1, r1))
print('strike2=%s, dip2=%s, rake2=%s' % (s2, d2, r2))
