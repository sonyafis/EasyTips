from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from auth_app.authentication import SessionAuthentication
from auth_app.serializers import UserDataSerializer


@api_view(['GET', 'PUT'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def profile(request):
    user_data = request.user

    if request.method == 'GET':
        serializer = UserDataSerializer(user_data)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserDataSerializer(user_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile completed', 'user_data': serializer.data})
        return Response(serializer.errors, status=400)