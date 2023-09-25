# -*- encoding: utf-8 -*-
"""
Copyright (c) 2023 - present Atbion<atbion.com>
Yadisnel Galvez Velazquez <yadisnel@atbion.com>
"""

from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from graphene_django.settings import graphene_settings
from graphene_django.views import GraphQLView, HttpError


class NucleoniGraphQLView(GraphQLView):
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        try:
            if request.method.lower() not in ("get", "post"):
                raise HttpError(
                    HttpResponseNotAllowed(
                        ["GET", "POST"], "GraphQL only supports GET and POST requests."
                    )
                )

            data = self.parse_body(request)
            show_graphiql = self.graphiql and self.can_display_graphiql(request, data)

            if request.method.lower() == "get":
                show_graphiql = True

            if show_graphiql:
                return self.render_graphiql(
                    request,
                    # Dependency parameters.
                    whatwg_fetch_version=self.whatwg_fetch_version,
                    whatwg_fetch_sri=self.whatwg_fetch_sri,
                    react_version=self.react_version,
                    react_sri=self.react_sri,
                    react_dom_sri=self.react_dom_sri,
                    graphiql_version=self.graphiql_version,
                    graphiql_sri=self.graphiql_sri,
                    graphiql_css_sri=self.graphiql_css_sri,
                    subscriptions_transport_ws_version=self.subscriptions_transport_ws_version,
                    subscriptions_transport_ws_sri=self.subscriptions_transport_ws_sri,
                    graphiql_plugin_explorer_version=self.graphiql_plugin_explorer_version,
                    graphiql_plugin_explorer_sri=self.graphiql_plugin_explorer_sri,
                    # The SUBSCRIPTION_PATH setting.
                    subscription_path=self.subscription_path,
                    # GraphiQL headers tab,
                    graphiql_header_editor_enabled=graphene_settings.GRAPHIQL_HEADER_EDITOR_ENABLED,
                    graphiql_should_persist_headers=graphene_settings.GRAPHIQL_SHOULD_PERSIST_HEADERS,
                )

            if self.batch:
                responses = [self.get_response(request, entry) for entry in data]
                result = "[{}]".format(
                    ",".join([response[0] for response in responses])
                )
                status_code = (
                    responses
                    and max(responses, key=lambda response: response[1])[1]
                    or 200
                )
            else:
                result, status_code = self.get_response(request, data, show_graphiql)

            return HttpResponse(
                status=status_code, content=result, content_type="application/json"
            )

        except HttpError as e:
            response = e.response
            response["Content-Type"] = "application/json"
            response.content = self.json_encode(
                request, {"errors": [self.format_error(e)]}
            )
            return response
