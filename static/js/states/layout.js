define([
  'app',
  'utils/time'
], function(app, time) {
  'use strict';

  return {
    abstract: true,
    templateUrl: 'partials/layout.html',
    controller: function($scope, $rootScope, $location, $window, authData,
                         projectList, adminMessage, flash, PageTitle) {
      PageTitle.set('Changes');

      $scope.appVersion = $window.APP_VERSION;
      $scope.projectList = projectList.data;
      $scope.user = authData.user;
      $scope.activeUser = $scope.user;
      $scope.authenticated = authData.authenticated;
      $scope.projectSearchQuery = {
        query: null,
        source: null
      };

      $scope.searchBuilds = function() {
        if (!$rootScope.activeProject) {
          return false;
        }

        $location.path('/projects/' + $rootScope.activeProject.slug + '/builds/').search(this.projectSearchQuery);

        return false;
      };

      // TODO: this should be replaced w/ project inheritance
      $scope.$on('$stateChangeSuccess', function(_u1, _u2, $stateParams){
        $scope.projectSearchQuery = $location.search();

        if (!$stateParams.project_id) {
          $rootScope.activeProject = null;
        } else if ($rootScope.activeProject && $stateParams.project_id != $rootScope.activeProject.slug) {
          $rootScope.activeProject = null;
        }
        // Display admin/system message if one has been set
        if (adminMessage && adminMessage.message) {
          var msgTxt = adminMessage.message;
          if (adminMessage.user && adminMessage.user.email) {
            msgTxt += ' - Posted by ' + adminMessage.user.email;
          }
          if (adminMessage.dateCreated) {
              msgTxt += ' (' + time.timeSince(adminMessage.dateCreated) + ')';
          }
          flash('warning', msgTxt, false);
        }
      });

      $rootScope.$on('$stateChangeError', function(event, toState, toParams, fromState, fromParams, error) {
        flash('error', 'There was an error loading the page you requested :(');
        // this should really be default behavior
        throw error;
      });

      $('.navbar .container').show();
    },
    resolve: {
      adminMessage: function($http) {
        return $http.get('/api/0/messages/').then(function(response) {
          return response.data;
        });
      },
      projectList: function($http) {
        return $http.get('/api/0/projects/');
      },
      // TODO: move auth into service
      authData: function($http) {
        return $http.get('/api/0/auth/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
