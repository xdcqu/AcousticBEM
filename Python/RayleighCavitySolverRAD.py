# ---------------------------------------------------------------------------
# Copyright (C) 2018 Frank Jargstorff
#
# This file is part of the AcousticBEM library.
# AcousticBEM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# AcousticBEM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AcousticBEM.  If not, see <http://www.gnu.org/licenses/>.
# ---------------------------------------------------------------------------
from RayleighCavitySolver import *
from BoundaryData import *
from Geometry import *

bOptimized = True
if bOptimized:
    from HelmholtzIntegralsRAD_C import *
else:
    from HelmholtzIntegralsRAD import *        


class RayleighCavitySolverRAD(RayleighCavitySolver):
    def __init__(self, aVertex, aElement, nOpenElements, c = 344.0, density = 1.205):
        super(RayleighCavitySolverRAD, self).__init__(aVertex, aElement, nOpenElements, c, density)
        self.aCenters      = (self.aVertex[self.aElement[:, 0]] +\
                              self.aVertex[self.aElement[:, 1]]) / 2.0
        # area of the boundary alements
        self.aLength = np.empty(self.aElement.shape[0], dtype=np.float32)
        self.aNormals = np.empty((self.aElement.shape[0], 2), dtype=np.float32)
        for i in range(self.aLength.size):
            a = self.aVertex[self.aElement[i, 0], :]
            b = self.aVertex[self.aElement[i, 1], :]
            ab = b - a
            vNormal = np.empty_like(ab)
            vNormal[0] = ab[1]
            vNormal[1] = -ab[0]
            nNorm = norm(vNormal)
            self.aNormals[i] = vNormal / nNorm
            self.aLength[i] = nNorm

    def cavityNormals(self):
        return self.aNormals[self.nOpenElements:self.numberOfElements(), :]

    def solveBoundary(self, k, boundaryCondition):
        M = self.computeBoundaryMatrix(k,
                                       boundaryCondition.alpha,
                                       boundaryCondition.beta)
        numberOfElements = self.totalNumberOfElements()
        b = np.zeros(2*numberOfElements, dtype=np.complex64)
        b[numberOfElements + self.nOpenElements: 2*numberOfElements] = boundaryCondition.f
        x = np.linalg.solve(M, b)
        
        return RayleighCavityBoundarySolution(self, boundaryCondition, k,
                                              x[0:numberOfElements],
                                              x[numberOfElements:2*numberOfElements])

    def computeBoundaryMatrix(self, k, alpha, beta):
        m = self.nOpenElements
        n = self.totalNumberOfElements() - m
        M = np.zeros((2*(m+n), 2*(m+n)), dtype=np.complex64)

        # Compute the top half of the "big matrix".
        for i in range(m+n):
            p = self.aCenters[i]
            for j in range(m+n):
                qa = self.aVertex[self.aElement[j, 0]]
                qb = self.aVertex[self.aElement[j, 1]]

                elementM  = ComputeM(k, p, qa, qb, i==j)
                elementL  = ComputeL(k, p, qa, qb, i==j)

                M[i, j]         = -elementM
                M[i, j + m + n] =  elementL

            M[i, i] -= 0.5 # subtract half a "identity matrix" from the M-factor submatrix

        # Fill in the bottom half of the "big matrix".
        M[m+n:2*m+n, 0:m]               = np.eye(m, dtype=np.float32)
        M[2*m+n:2*(m+n), m:m+n]         = np.diag(alpha)
        M[m+n:2*m+n, m+n:2*m+n]         = 2.0 * M[0:m, m+n:2*m+n]
        M[2*m+n:2*(m+n), 2*m+n:2*(m+n)] = np.diag(beta)
        return M

    def solveInterior(self, solution, aSamples):
        aPhi = np.empty(aSamples.shape[0], dtype=complex)

        for i in range(aSamples.shape[0]):
            p = aSamples[i,:]
            sum = 0.0
            for j in range(solution.aPhi.size):
                qa = self.aVertex[self.aElement[j, 0]]
                qb = self.aVertex[self.aElement[j, 1]]

                elementL  = ComputeL(solution.k, p, qa, qb, False)
                elementM  = ComputeM(solution.k, p, qa, qb, False)
                sum += elementL * solution.aV[j] - elementM * solution.aPhi[j]
            aPhi[i] = sum

        return SampleSolution(solution, aPhi)

    def solveExterior(self, solution, aSamples):
        aPhi = np.empty(aSamples.shape[0], dtype=complex)

        for i in range(aSamples.shape[0]):
            p = aSamples[i,:]
            sum = 0.0
            for j in range(self.nOpenElements):
                qa = self.aVertex[self.aElement[j, 0]]
                qb = self.aVertex[self.aElement[j, 1]]

                elementL  = ComputeL(solution.k, p, qa, qb, False)
                sum += -2.0 * elementL * solution.aV[j]
            aPhi[i] = sum

        return SampleSolution(solution, aPhi)
